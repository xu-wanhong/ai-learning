# Day 26 · httpx 同步 vs 异步（真实 HTTP 请求）

2026-09-25 · Python 3.13 · macOS · 下面的输出都是本机实测

今天第一次把 asyncio 用在**真实的网络请求**上。

一句话结论：**同步 10 个请求要 10.09s，异步只要 1.06s —— 9.48 倍。**

---

## 一、先跑通：自己写的三个版本

### 1. 同步串行（`my_sync.py`）

```python
import time
import httpx

BASE = "http://127.0.0.1:8765"

t0=time.perf_counter()
with httpx.Client(timeout=10) as client:
    for i in range(3):
        r = client.get(f"{BASE}/page{i}")
        print(f"page{i} :{r.status_code}")

print(f"3个串行请求总耗时{time.perf_counter()-t0:.2f}s")
```

```
page0 :200
page1 :200
page2 :200
3个串行请求总耗时3.05s
```

### 2. 异步并发（`my_async.py`）

```python
async def fetch(client,i):
    r = await client.get(f"{BASE}/page{i}")
    return f"page{i}: {r.status_code}"

async def main():
    t0=time.perf_counter()
    async with httpx.AsyncClient(timeout=10) as client:
        r = await asyncio.gather(*(fetch(client,i) for i in range(3)))
    for line in r:
        print(line)
    print(f"三个异步请求总耗时:{time.perf_counter()-t0:.2f}s")
```

```
page0: 200
page1: 200
page2: 200
三个异步请求总耗时:1.05s
```

**3.05s → 1.05s，2.90 倍。**

### 3. 挑战题：队列 + 消费者（`my_queue_download.py`）

生产者扔 9 个地址进队列，3 个消费者并发下载：

```
生产：page0 ... 生产：page8
消费者0 完成 .../page0 → 200
消费者2 完成 .../page2 → 200
消费者1 完成 .../page1 → 200
...
成功 9/9 个，耗时 3.07s
```

**9 个任务 ÷ 3 个消费者 × 1 秒 = 3.0s** ✅

**这三个脚本合起来，就是 Day 27 那个「AI 任务调度器」的雏形。**

---

## 二、`httpx` 只差一个类名

| 同步 | 异步 |
|---|---|
| `httpx.Client()` | `httpx.AsyncClient()` |
| `with ... as client:` | `async with ... as client:` |
| `client.get(url)` | `await client.get(url)` |
| `for` 循环 | `asyncio.gather(...)` |

和 Day 22 的 `ThreadPoolExecutor` / `ProcessPoolExecutor` 是同一个套路。

**注意 `AsyncClient` 要建一次、共用**（`async with` 包住整段）——
如果每个消费者各建一个客户端，**连接池就白搭了**。

---

## 三、今天的实测数据

### 三个请求 vs 十个请求

| 实验 | 任务数 | 同步 | 异步 | 加速比 |
|---|---|---|---|---|
| `my_sync` / `my_async` | 3 | 3.05s | 1.05s | **2.90x** |
| `ex2` / `ex3` | 10 | 10.09s | 1.05s | **9.61x** |

### benchmark.py（10 个请求，控制变量）

```
N = 10 个请求，服务器每个睡 1s，理论最优 1.0s

同步串行 httpx.Client      : 10.09s   加速比 1.00x
异步并发 AsyncClient       : 1.06s   加速比 9.48x
异步外壳 + 同步 httpx.get  : 10.35s   加速比 0.98x
```

**第三行请盯三秒：0.98x —— 比同步还慢。**

`ex4.py` 里那段代码有 `async def`、有 `gather`、有 `await`，**一应俱全，但一点并发都没有**，因为里面调的是同步的 `httpx.get()`。

> 和 Day 23 那个 `gather` + `time.sleep` 的 `0.99x` **是同一个数字、同一个病**。
> **只要内层不让位，外层写多少 `async` 都是装饰。**

### 为什么是 9.48x 而不是 10.00x

那 0.06s 是固定开销：建连接、事件循环调度、创建任务、收集结果。

**加速比永远达不到理论上限** —— 每次都有固定开销在里面（和 Day 22 学的"进程池启动开销固定"是同一条道理）。

---

## 四、踩的坑（今天踩了一堆，这条最厚）

### 1. 把 Python 代码敲进了终端

```
zsh: command not found: import
zsh: command not found: URL
zsh: number expected
```

**原因**：终端只认命令，不认 Python 代码。

**判别法（很有用）**：

| 报错开头 | 谁报的 | 说明 |
|---|---|---|
| `zsh:` / `bash:` | **shell** | **命令敲错了**（或者把代码敲进了终端） |
| `Traceback` | **Python** | 代码出错了 |

**看到 `%` 结尾的提示符 = 你在终端里，只能敲命令。** 写代码要在 VS Code 的编辑区。

### 2. `ModuleNotFoundError: No module named 'httpx'`

**原因**：忘了跑 `uv add httpx`。

**排查动作**：

```bash
which python
```

- 出 `.../ai-learning/.venv/bin/python` → 环境对，那就是**没装** → `uv add httpx`
- 出 `/usr/bin/python3` → **虚拟环境没激活** → `source .venv/bin/activate`

**这个报错 90% 就这两个原因，`which python` 是照妖镜。**

### 3. `item = q.get()` 少写 `await` ⚠️

```python
item=q.get()                              # ❌ 拿到的是协程对象
print(f"{name}:完成{item}")                # 打印 <coroutine object Queue.get at 0x...>
q.task_done()                             # 照样打勾了
```

**两个后果**：

- 打印出来是 `<coroutine object ...>`，不是地址
- **队列里的东西一个都没被取走** —— 但 `task_done()` 照打不误

### 4. ⚠️ 队列不知道你在撒谎：`get()` 和 `task_done()` 是解耦的

队列内部只有一个计数器：

| 动作 | 计数器 `_unfinished_tasks` |
|---|---|
| `put()` | **+1** |
| `task_done()` | **−1**，减到 0 唤醒 `join()` |
| **`get()`** | **不动** |

**计数器只知道"put 了 9 次"，它根本不知道你有没有真的取货。**

所以即使一个都没取到，9 次 `task_done()` 之后 `q.join()` 也会"正常"返回。

> **这是 `asyncio.Queue` 给不了你的保护：配不配对，得你自己保证。**

### 5. `while True` 里一个 `await` 都没有 → 独占事件循环

崩溃前的输出分布出卖了它：

```
消费者0: ... × 10 次      ← 独占！
消费者1: ... × 1 次
消费者2: ... × 1 次
```

**原因**：那个循环里 `q.get()` 没 await，`print` 和 `task_done()` 都是同步的 → **协程从不挂起 → 事件循环拿不回控制权** → 消费者0 一路跑到底。

它为什么停了？计数器发火：

- 前 9 次 `task_done()`：9 → 0，正常
- 第 10 次：`_unfinished_tasks <= 0` → **`ValueError: task_done() called too many times`** → 消费者0 崩溃，事件循环才拿回控制权
- 消费者1、2 接着启动，第一次打勾就撞上 0 → 各崩一次（所以各只有 1 行 print）

> **「10 / 1 / 1」这个分布，就是"某个协程独占事件循环直到崩溃"的指纹。**
> **`while True` 的协程里必须至少有一个 `await`。**

### 6. 崩溃了却一点报错都看不到 —— `return_exceptions=True` 把异常吞了

```python
await asyncio.gather(*workers, return_exceptions=True)
#                                             ↑ 3 个 ValueError 被当成"正常结果"收下
```

**退出码 0、屏幕干净、数据全错。**

Day 25 学它是为了让 `CancelledError` 别炸掉 `main` —— **但它同时也把真 bug 一起吞了。**

> **调试期的纪律**：先用 `return_exceptions=False`，或者把返回的列表 print 出来看一眼。
> **「退出码 0」不等于「没错」。**

### 7. `0.00s` 是警报，不是好消息

第一次跑挑战题，输出是：

```
九个任务全部处理完耗时：0.00s
```

**因为整个程序一个 HTTP 请求都没发过** —— 没有请求，就没有那 1 秒等待，只剩 print 和计数器，微秒级跑完。

**`0.00s` 不是"很快"，是"什么都没做"。**

验收标准写 `≈3.0s` 的意义就在这里：**它是一个警报器。**

### 8. 地址拼错：`pang` 写成了 `page`

```python
await q.put(f"{BASE}/pang{b}")     # ❌
```

**这次没暴露**，因为我们的假服务器**不判断路径**（见下一节）。
**换成真网站，这 9 个请求全是 404** —— 而且 `httpx` 不会报错。

### 9. `httpx` 不会因为 4xx/5xx 报错 ⚠️

```python
r = client.get("http://某个挂了的地方/page0")
print(r.status_code)      # 500
# 程序一点都不报错，继续往下跑 —— 你以为成功了
```

要它抛异常，得自己喊：

```python
r.raise_for_status()
```

**所以 `print(r.status_code)` 不是装饰，是数据卫生检查。**

> 如果 10 个请求全是 404（地址写错了），`benchmark.py` 照样给你一个漂亮的 `10.09s` —— **但那测的是垃圾。**

---

## 五、状态码 200 是怎么来的

**200 是服务器给的，不是 Python 给的。** 就是 `slow_server.py` 里的 `self.send_response(200)`。

它藏在响应报文第一行中间：

```
HTTP/1.0 200 OK
...
Content-Length: 18

hello from /page0
```

`httpx` 把这一行拆开，把中间的 `200` 塞进 `r.status_code`。

### 实测：为什么**全是** 200

```
GET  /page0        → 200   hello from /page0
GET  /page999      → 200   hello from /page999        ← 不存在的路径也是 200
GET  /根本不存在    → 200   hello from /%E6%A0%B9...   ← 乱写也是 200
POST /page0        → 501
```

**因为我们的假服务器根本不判断路径**：

```python
def do_GET(self):
    time.sleep(DELAY)
    body = f"hello from {self.path}\n".encode("utf-8")   # path 只是被拼进内容
    self.send_response(200)                               # 无条件 200
```

**200 不是"自动的"** —— 换成 POST 就返回 **501 Not Implemented**，因为 `SlowHandler` 里只写了 `do_GET`，没有 `do_POST`。

> 200 的完整含义：**「这个请求有对应的处理函数，并且它处理成功了」** —— 两个条件都要。

---

## 六、⭐ 改一处：把服务器改成单线程（今天的高潮）

> ⚠️ **这一步我还没做**，下面的数据是我先跑的 —— 你自己跑一遍确认。

把 `slow_server.py` 里的**一个词**改掉：

```python
from http.server import BaseHTTPRequestHandler, HTTPServer      # 去掉 Threading
...
HTTPServer(("127.0.0.1", PORT), SlowHandler).serve_forever()
```

重启服务器，再跑 `ex3.py`：

```
异步并发 10 个请求：10.09s
```

**和同步串行的 10.09s 一模一样 —— 并发完全白搭。**

### 为什么

`HTTPServer` **一次只处理一个请求**。你把 10 个请求同时扔过去，服务器乖乖排队，一个一个睡完 1 秒。

### 这条把 Day 25 的公式补全了

Day 25 我写的是 `加速比上限 = min(任务数, 并发度)`。**今天要补上第三项：**

> ### 加速比上限 = `min(任务数, 客户端并发度, 服务端并发度)`

| 服务器 | 服务端并发度 | `min(10, 10, ?)` | 实测 |
|---|---|---|---|
| `ThreadingHTTPServer` | 10 | 10 | 1.06s（**9.48x**） |
| `HTTPServer`（单线程） | **1** | **1** | 10.09s（**1.00x**） |

> **你能拿到的加速比，永远被链路里最窄的那一段卡住。**

**这在 AI 应用里天天遇到**：你的异步服务写得飞快，但下游向量库只允许 5 个并发连接 —— 上限就是 5，写再多 `async` 都没用。

改完**记得把 `ThreadingHTTPServer` 改回来**。

---

## 七、和 Day 23 / 24 / 25 的连线

| 天 | 上限公式的那一项 | 实测 |
|---|---|---|
| Day 22 | 任务数 / 线程数（4） | 3.99x |
| Day 24 | 任务数（10） | 9.99x |
| Day 25 | 消费者数（9 / 3 / 1） | 8.99x / 3.00x / 1.00x |
| **Day 26** | **＋ 服务端并发度（10 / 1）** | **9.48x / 1.00x** |

**五天、四个不同的机制（线程池 / gather / 队列 / HTTP），全部落在同一条公式上。**

---

## 八、还没搞懂的

1. `raise_for_status()` 和手动检查 `status_code` 各适合什么场景？
2. 那个 0.06s 的固定开销具体花在哪？怎么测出来？
3. `Semaphore` 限流和"服务端并发度"是什么关系？（Day 28 会讲）
