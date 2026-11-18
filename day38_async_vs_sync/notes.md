# Day 38 · `async def` 还是 `def`

2026-11-18 · macOS · FastAPI 0.162.0

> **今天只有一个概念：接口函数该写 `async def` 还是 `def`。**
>
> **选错了，性能差 10 倍，而且不报错。**

---

## 一、⭐ 三条规则（先记住这个）

| 你的接口里会做什么 | 写哪个 | 例子 |
|---|---|---|
| **调用「有 `await` 的库」** | **✅ `async def`** | `httpx.AsyncClient`、`asyncio.sleep`、`aiofiles` |
| **调用「没有 `await` 的老库」** | **🟡 `def`** | `requests`、`time.sleep`、PIL、老 SDK |
| **纯计算（算数、拼字符串）** | **🟡 `def`** | —— |

**❌ 绝对不要：`async def` 里调同步阻塞函数。**

---

## 二、实测：三个组合差 10 倍

**10 个并发请求，每个接口内部要等 0.5 秒**（`day38_async_vs_sync/app.py` + `bench.py`）：

```
  ✅ async def + await asyncio.sleep      →  0.52s
  ❌ async def + time.sleep（阻塞）        →  5.06s
  🟡 def + time.sleep（线程池）             →  0.52s
```

| 写法 | 耗时 | 为什么 |
|---|---|---|
| **`async def` + `await asyncio.sleep`** | **0.52s** | `await` 让出控制权，10 个一起等 |
| **`async def` + `time.sleep`** | **5.06s** | **`time.sleep` 不让出**，把事件循环按住，10 个排队 |
| **`def` + `time.sleep`** | **0.52s** | FastAPI 自动丢进**线程池**执行，不堵事件循环 |

> ### ⚠️ 最反直觉的一条
> **`def` + `time.sleep` 和 `async def` + `await` 一样快！**
> **因为 FastAPI 对 `def` 接口会自动 `run_in_executor` 到线程池**（Day 30 学的那个）。
>
> **唯一会"堵死"的组合是 `async def` + 同步阻塞函数。**

---

## 三、为什么（时间线）

### ✅ `async def` + `await`

```
请求1 ──等待0.5s──────────┐
请求2 ──等待0.5s──────────┤
...                       ├─→ 0.52s 全部完成
请求10 ──等待0.5s─────────┘
```

### ❌ `async def` + `time.sleep`

```
请求1 ─死等0.5s─┐
                ├─ 请求2 才能开始 ─死等0.5s─┐
                                            ├─ 请求3 ...
→ 10 × 0.5 = 5 秒
```

**`time.sleep` 是"死等"** —— **这 0.5 秒里事件循环处理不了任何请求**（连别的接口也被堵住）。

---

## 四、怎么判断"我调的这个东西是不是阻塞的"

**看有没有 `await`。**

```python
# ✅ 有 await 的库（异步库）
await httpx.AsyncClient().get(url)        # Day 26 学过
await asyncio.sleep(1)
await aiofiles.open(...)
await redis.asyncio...

# ❌ 没有 await 的（同步库）
requests.get(url)                         # 阻塞
time.sleep(1)                             # 阻塞
PIL.Image.open(...)                       # 阻塞
open("大文件").read()                      # 阻塞（大文件时）
```

**接口写法判断**：

```python
async def my_api():
    await httpx_client.get(...)       # ✅ 完美
```

```python
async def my_api():
    requests.get(...)                 # ❌ 灾难（堵死事件循环）
```

**三种修法**：

```python
# 修法 1：换成异步库（最好）
await httpx_client.get(...)

# 修法 2：把同步函数丢进线程池（Day 29 学的 to_thread）
await asyncio.to_thread(requests.get, url)

# 修法 3：干脆改成 def 接口（代码一行不改）
@app.get("/x")
def x():
    requests.get(...)
```

---

## 五、题 2 实测：5 个接口对比

**`day38_async_vs_sync/slow_app.py` + `bench_slow.py`**（需要先起 `downstream.py` 在 8078）：

```
  /slow-ok    →  0.52s   状态码 {200}      async def + await asyncio.sleep    ✅ 对照
  /slow-bad   →  5.10s   状态码 {200}      async def + requests.get           ❌ 病态
  /slow-fix1  →  0.65s   状态码 {200}      await httpx                        ✅ 修法1
  /slow-fix2  →  0.52s   状态码 {200}      asyncio.to_thread(requests.get)    ✅ 修法2
  /slow-fix3  →  0.52s   状态码 {200}      def + requests.get                 ✅ 修法3
```

**三种修法都有效**，选哪个看情况：

| 修法 | 什么时候用 |
|---|---|
| **换成 `httpx`** | 能换库时（最好） |
| **`asyncio.to_thread`** | 换不了库（老 SDK、付费 SDK） |
| **改成 `def`** | 整个接口都以同步为主 |

---

## 六、⚠️ 题 2 踩的大坑：**不能在自己身上调自己**

**我第一版写错了** —— 让 `/slow-bad` 用 `requests.get` 调**同一个服务**的 `/slow-target`：

```
/slow-bad 里 requests.get(自己的 /slow-target)
   ↓
requests.get 把事件循环按住
   ↓
/slow-target 也在同一个事件循环上 → 永远轮不到它响应
   ↓
死锁 → 10 秒超时 → 500 Internal Server Error
```

**实测**：

```
/slow-target 单独测 → 200  0.51s   （它自己没问题）
/slow-bad          → 500  10.009s  （卡到超时）
```

**修法**：**必须开两个进程**（8077 主服务、8078 下游）。

> **这个坑在真实项目里也常见** —— 「我的接口调自己的另一个接口」。
> **并发一高就死锁。**
>
> **正确做法**：把公共逻辑抽成**普通函数**直接调，**不要走 HTTP 绕一圈**。

---

## 七、真实 AI 应用里怎么选

**你的 RAG 服务**：

```python
@app.post("/chat")
async def chat(req: ChatRequest):
    # ① 调 LLM —— httpx 异步版（1~30 秒，必须异步）
    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.openai.com/...", json=...)

    # ② 查向量库 —— 看库有没有异步版
    docs = await vector_store.asearch(...)     # 有就用 await

    # ③ 算 token 数 —— 纯 CPU，毫秒级
    n = len(answer)                             # 同步没关系

    return {"answer": answer}
```

**判断标准**：

| 这一步 | 多久 | 用什么 |
|---|---|---|
| **调 LLM** | **1~30 秒** | **`async def` + `await`** ✅ |
| **查向量库** | 10~100 毫秒 | 有异步版就用 |
| **算 token / 拼字符串** | 微秒~毫秒 | 同步无所谓 |

> **判断标准：这一步「等」的时间长不长？**
> **等得久（> 50ms）→ 必须异步（`await`）。**
> **等得短（毫秒级）→ 同步不影响。**

---

## 八、踩的坑

| # | 现象 | 原因 | 修法 |
|---|---|---|---|
| **1** | **单测正常，并发一上来就慢 10 倍** | **`async def` 里调了同步库** | 换异步库 / `to_thread` / 改 `def` |
| 2 | `SyntaxError: 'await' outside async function` | **`def` 接口里写了 `await`** | 改成 `async def` |
| 3 | 并发超过几十个就卡 | **线程池有上限** | 高并发用 `async def` |
| 4 | `async def` 里跑大循环也卡 | **`async` 只解决"等"，不解决"算"** | 上进程池（Day 30） |
| **5** | **500 + 卡 10 秒** | **接口调自己 → 死锁** | 抽成普通函数直接调 |

### 坑 1 为什么最难查

```python
async def my_api():
    requests.get(...)      # 没有 await，不报错，单测也过
    return {...}
```

**表现**：**单测正常、并发一上来就慢得离谱**。

**怎么发现**：**压测**（同时发 10 个请求看总耗时）。

---

## 九、命令速查

```bash
cd ~/dev/ai-learning/day38_async_vs_sync

# 题1：三组合对比
../.venv/bin/python -m uvicorn app:app --port 8000       # 终端 A
../.venv/bin/python bench.py                             # 终端 B

# 题2：5 接口对比（要先起下游）
../.venv/bin/python -m uvicorn downstream:app --port 8078   # 终端 A
../.venv/bin/python -m uvicorn slow_app:app --port 8077     # 终端 B
../.venv/bin/python bench_slow.py                           # 终端 C

# 清端口
kill $(lsof -ti :8000) $(lsof -ti :8077) $(lsof -ti :8078) 2>/dev/null
```

---

## 十、还没搞懂的

1. FastAPI 的线程池默认有几十个线程？具体数字是多少？怎么调？
2. `asyncio.to_thread` 和 `run_in_executor(进程池)` 什么时候各用哪个？
3. 如果坚持用 `async def` + 同步库，除了慢，还会有什么后果（比如超时、连接泄漏）？
4. `uvicorn --workers 4` 和 `async def` 是什么关系？多进程能绕过这个问题吗？
5. Starlette 的 `run_in_threadpool` 和 `asyncio.to_thread` 有什么区别？
