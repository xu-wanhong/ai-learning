# Day 25 · asyncio.Queue 与生产者消费者模型

2026-09-23 ~ 09-24 · Python 3.13 · macOS · 下面的输出都是本机实测

今天要回答的是 Day 24 结尾留下的那个问题：**多个任务同时读写同一份数据，为什么 asyncio 不用加锁？**

答案是「有边界」—— ex4 把那条边界踩穿了，结果比我预想的狠。

---

## 一、队列的核心：`get()` 在空队列上会挂起

ex1 就是最基础的操作：

```python
q = asyncio.Queue()
await q.put("b")
await q.put("t")

print("放进去两个，qsize=", q.qsize())

print("取出", await q.get())
print("取出", await q.get())

print("qsize =", q.qsize(), " empty =", q.empty())
```

```
放进去两个，qsize= 2
取出 b
取出 t
qsize = 0  empty = True
```

FIFO，先进先出。这没什么好说的，重要的是下面这个「改一处」。

### 改一处：再 get 一次会怎样

在最后加一行 `print("取出：", await q.get())`。

**结果不是报错，是程序永久卡住** —— 不报错、不退出、光标就在那儿闪，只能 `Ctrl+C`。

> **`await` 一个空队列 = 无限期挂起。**

**这就是生产者消费者模型能成立的根基**：消费者不用轮询（不用写 `while q.empty(): 再等等`），没活儿干就挂在那儿，有活儿了自动被唤醒 —— CPU 一点不浪费。

同一个行为：

- 在 ex1 里是 **bug**（没人再 put 了）
- 在 ex2/ex3 里是 **特性**（生产者总会来 put）

---

## 二、生产者消费者：总耗时跟着「慢的那条线」走

```python
async def producer(q, n):
    for i in range(n):
        await asyncio.sleep(0.2)      # 生产一个 0.2s
        await q.put(f"任务{i}")
        print(f"  生产：任务{i}")

async def consumer(q, name, n):
    for _ in range(n):
        item = await q.get()
        await asyncio.sleep(0.5)      # 处理一个 0.5s
        print(f"{name} 处理完：{item}")
```

实测输出：

```
  生产：任务0
  生产：任务1
  生产：任务2
消费者 处理完：任务0
  生产：任务3
  生产：任务4
消费者 处理完：任务1
消费者 处理完：任务2
消费者 处理完：任务3
消费者 处理完：任务4
总耗时：2.71s
```

**读这段输出**：生产快（0.2s/个）、消费慢（0.5s/个），所以队列里**会堆积** —— 前 3 个任务几乎立刻生产出来全堆着，消费者慢悠悠一个一个取。

**关键结论：**

```
生产总时间：5 × 0.2s = 1.0s
消费总时间：5 × 0.5s = 2.5s
总耗时 ≈ max(1.0, 2.5) = 2.5s      实测 2.71s
```

> **总耗时由最慢的那一方决定，不是两边相加（3.5s）。**

多出来的 0.21s 是启动开销 + 队列交互的开销。

**这条的实际意义**：想提速就去优化**慢的那一边**。生产只有 1.0s，把它优化到 0.5s 对总耗时**一点用都没有** —— 瓶颈在消费。

**改一处**：把消费者改成 `0.1`（比生产快）。总耗时应该降到 ≈ 1.0s —— 慢的那条线换人了。

---

## 三、怎么知道「全干完了」：`task_done()` + `join()`

ex3 是 1 个生产 + 3 个消费。这里的难点是：**消费者写的是 `while True`，它自己不知道要处理几个。**

```python
async def consumer(q, name):
    while True:
        item = await q.get()
        await asyncio.sleep(0.3)
        print(f"{name} 完成 {item}")
        q.task_done()          # ← 没有 await！它是普通方法
```

实测输出（看那三个消费者，严格轮流，一个不漏一个不重）：

```
  生产：任务0
  生产：任务1
  生产：任务2
消费者0 完成 任务0
  生产：任务3
消费者1 完成 任务1
  生产：任务4
消费者2 完成 任务2
  生产：任务5
消费者0 完成 任务3
  生产：任务6
消费者1 完成 任务4
  生产：任务7
消费者2 完成 任务5
  生产：任务8
消费者0 完成 任务6
消费者1 完成 任务7
消费者2 完成 任务8
--- 9 个任务全部处理完，耗时 1.11s ---
```

### 队列内部只有一个计数器

我把本机 `asyncio/queues.py` 的源码翻出来看了：

```python
def task_done(self):
    if self._unfinished_tasks <= 0:
        raise ValueError('task_done() called too many times')
    self._unfinished_tasks -= 1
    if self._unfinished_tasks == 0:
        self._finished.set()

async def join(self):
    if self._unfinished_tasks > 0:
        await self._finished.wait()
```

| 动作 | 计数器 `_unfinished_tasks` |
|---|---|
| `put()` 放进一个 | **+1** |
| `task_done()` | **−1**，减到 0 就唤醒 `join()` |
| **`get()` 取走一个** | **不变** |

### ⚠️ 我这里搞错过一次

我一开始以为「消费者 `get` 一个，计数器就自动减一」。**不对 —— `get` 一点都不减。**

`put` 和 `task_done` 是两个手动配对的动作，`get` 夹在中间不参与计数。

**为什么必须这样设计？** 因为 `get` 只代表「我**拿到**了」，不代表「我**处理完**了」—— 中间可能还要跑 10 秒的活儿。计数必须由消费者在真正做完之后自己报。

### 漏掉 / 多调，后果正好相反

- **漏调 `task_done()`** → 计数永远归不了零 → **`join()` 永远不返回，程序静默卡死**（不报错、不退出，跟第一节那个空 `get` 一个死法）
- **多调 `task_done()`** → **立刻报错**：`ValueError: task_done() called too many times`

> **少调静默卡死，多调立刻报错。** 以后遇到卡死的程序，第一个怀疑对象就是它。

### 1.11s 是怎么来的

```
生产：9 × 0.1s = 0.9s
消费：9 × 0.3s ÷ 3 人 = 0.9s
```

两边速度刚好相等 → **流水线并行** → 实测 1.11s，多出来的 0.21s 是「最后一批任务还得等 0.3 秒」的尾巴。

### 收尾为什么要那两行

```python
for w in workers:
    w.cancel()
await asyncio.gather(*workers, return_exceptions=True)
```

消费者是 `while True`，**永远不会自己结束**，必须主动取消。

但 `cancel()` **不是立刻杀掉**，它只是**发出一份取消请求**：打断任务当前正在等的那个 future，让 `CancelledError` 在任务内部抛出来 —— 这需要**下一个事件循环轮次**才生效。

所以 `cancel()` 之后要 `await gather(...)` 等它们真正结束，否则事件循环关闭时会报：

```
Task was destroyed but it is pending!
```

（Day 24 见过这个警告。）

而 `return_exceptions=True` 是为了**让 gather 别把 `CancelledError` 往外抛**把 main 炸掉 —— 把它当成普通结果收下来就行。

---

## 四、为什么不用锁（ex4）

先看结果。**注意：这个数字每次跑都不一样，但一定远小于 100。**

```python
async def safe_worker(q, box):
    while True:
        await q.get()
        box["n"] = box["n"] + 1     # 读-改-写，中间没有 await
        q.task_done()

async def risky_worker(q, box):
    while True:
        await q.get()
        tmp = box["n"]              # 读
        await asyncio.sleep(0)      # ← 让位点！别人能在这中间插进来
        box["n"] = tmp + 1          # 写
        q.task_done()
```

3 个消费者处理 100 个任务，实测：

```
期望值：100

安全版（读-改-写 中间没有 await）: 100
危险版（中间插了 sleep(0)）     : 34
```

**100 个任务只数到 34，丢了 66%。而且一声不吭 —— 没有报错、退出码 0、结果就是错的。**

又是那一族 bug。

### 规则

> **在 asyncio 里，两个 `await` 之间的代码不会被打断。**
>
> - 「读-改-写」**整段中间没有 `await`** → 它是一段不可分割的操作 → **不用锁** ✅
> - 你自己在中间插了一个 `await` → 别人就有机会插进来 → **丢数据** ❌

### 和 Day 22 的线程对照（根子上不是一回事）

| | 线程 | asyncio |
|---|---|---|
| 执行方式 | **真并行** —— 两个线程在同一瞬间都在跑 | **并发但不同时** —— 只有一个在跑，只是会交替 |
| 问题出在 | **同时**改同一块内存 | **读到一半被切走** |
| 什么时候可能被切走 | **任意一行**（操作系统时间片） | **只在 `await` 那一行** |
| 解法 | `threading.Lock`（把"同时"变成"先后"） | **不给它切换的机会** |

Day 22 学的 `Lock` 在这里用不上，**不是因为 asyncio 更高级，而是因为它把"切换点"从"任意一行"压缩到了"`await` 那一行"**。

检查点少了几万倍，撞车概率趋近于零 —— 但只要你在中间留一个 `await`，它立刻回来。

**`asyncio.Queue` 本身之所以不用锁，就是同一个原因**：它内部改队列状态的那几行是一气呵成的，不给任何人留缝。

---

## 五、消费者数 = 并发度

benchmark：9 个任务，每个 0.3s，只改消费者数量：

```
9 个任务，每个 0.3s，理论最优 0.3s

消费者数 = 1 : 2.71s   加速比 1.00x   已处理 9
消费者数 = 3 : 0.90s   加速比 3.00x   已处理 9
消费者数 = 9 : 0.30s   加速比 8.99x   已处理 9
```

**这就是 Day 22 `max_workers` 的 asyncio 版本** —— 只不过"工人"是自己用 `create_task` 造出来的协程：

| Day 22 | Day 25 |
|---|---|
| `ThreadPoolExecutor(max_workers=4)` | `[create_task(consumer(q)) for _ in range(4)]` |
| 影响**速度**，不影响**结果** | 一样 |

**这个直接对应目标岗位**：一个 RAG 服务同时进来 100 个请求，开 100 个线程内存撑不住，但开 100 个协程任务没问题。

---

## 六、一条公式，把 Day 22 / 24 / 25 串起来了

之前几天我一直把「加速比上限」当成两条分开的规律，今天才想明白是**一条公式的两个变量**：

> ### 加速比上限 = `min(任务数, 并发度)`

把跑过的所有数据代进去：

| 天 | 实验 | 任务数 | 并发度 | `min()` | 实测 |
|---|---|---|---|---|---|
| Day 22 | I/O，线程池(4) | 4 | 4 | **4** | 3.99x |
| Day 24 | `gather`，N=10 | 10 | 10 | **10** | 9.99x |
| Day 25 | 消费者 = 9 | 9 | 9 | **9** | 8.99x |
| Day 25 | 消费者 = 3 | 9 | 3 | **3** | 3.00x |
| Day 25 | 消费者 = 1 | 9 | 1 | **1** | 1.00x |

**五天、三个完全不同的机制（线程池 / gather / 队列），全部落在同一条公式上。**

两个方向都实用：

- **任务数不够，加人手白搭** —— 10 个任务配 100 个消费者，还是只能到 10x
- **人手不够，加任务白搭** —— 100 个任务配 1 个消费者，还是 1x

**被问到「怎么优化并发性能」时，答案就是这一句：先看瓶颈是任务数还是并发度。**

---

## 七、踩坑

1. **`await q.get()` 打在空队列上** → ⚠️ 永久挂起，不报错、不退出，只能 `Ctrl+C`
2. **`get()` 后忘了 `task_done()`** → `join()` 永远不返回（同样静默卡死）
3. **`task_done()` 调多** → `ValueError: task_done() called too many times`（这个反而会报错）
4. **误以为 `get()` 会让计数器 −1** → 不是，只有 `task_done()` 会
5. **「读-改-写」中间插了 `await`** → 静默丢数据（100 → 34）
6. **`while True` 消费者 `cancel()` 后直接结束** → `Task was destroyed but it is pending!`
7. **`cancel()` 后忘了 `return_exceptions=True`** → `CancelledError` 把 main 炸掉
