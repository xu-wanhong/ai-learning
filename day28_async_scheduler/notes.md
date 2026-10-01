# Day 28 · 调度器 V2（asyncio 版）+ Semaphore 限流

2026-09-30 ~ 10-01 · Python 3.13 · macOS · 下面的输出都是本机实测

今天把 Day 27 那个**线程池版调度器**用 asyncio 重写了一遍。

**一句话结论**：

> **`Semaphore(3)` 和 `max_workers=3` 是同一件事的两种表达。**
> 两种完全不同的机制（协程 vs 线程），**并发度一样 → 耗时几乎一样**。

---

## 一、成品

`day28_async_scheduler/scheduler_v2.py` —— asyncio 版调度器，`Semaphore(3)` 限流。

**实测输出**：

```
task_001 开始执行
task_002 开始执行
task_003 开始执行          ← 只有 3 个「开始」= 限流生效
task_002 执行结束
task_004 开始执行          ← 002 结束，004 才拿到名额
task_002 | jack  | success
task_001 执行结束
task_005 开始执行
task_001 | tom   | success
task_004 执行结束
task_006 开始执行
task_004 | lucy  | success
task_007 开始执行
task_003 | rose  | failed  | rose 执行失败
task_005 执行结束
task_008 开始执行
task_005 | bob   | success
task_006 | amy   | failed  | amy 执行失败
task_008 执行结束
task_008 | zoe   | success
task_007 执行结束
task_007 | ken   | success

成功 6 / 失败 2   总耗时 7.00s
```

---

## 二、三个核心概念

### 1. asyncio 版 = Day 27 的「换名字版」

| Day 27（线程池） | Day 28（asyncio） |
|---|---|
| `ex.submit(ai_task, ...)` → Future | `asyncio.create_task(ai_task(...))` → Task |
| `as_completed(future_map)` | **`asyncio.as_completed(future_map)`** |
| **`for`** | **`async for`** ⚠️ |
| `f.result()` | **`await f`** |
| `time.sleep(s)` | **`await asyncio.sleep(s)`** |
| `max_workers=3` | **`Semaphore(3)`** |

### 2. ⭐ `Semaphore(N)` ≈ `max_workers=N`

**为什么 asyncio 需要 `Semaphore`？** 因为**线程池有 `max_workers` 自动限流，asyncio 没有** —— 你一次 `create_task` 多少，就真的多少同时在跑。

**限流的两种写法**（`ex4.py`）：

| | 信号量模型 | 消费者模型 |
|---|---|---|
| 造几个 Task | **全部（8 个）** | **只造 3 个消费者** |
| 靠什么限制 | `Semaphore(3)` 守卫 | 工人数本身就是 3 |
| 适合 | 任务已知、一次性一批 | **任务源源不断** |
| 实测耗时 | **7.00s** | **7.00s** |

### 3. ⭐⭐ `asyncio.as_completed` 必须配 `async for`

**这是今天最大的坑，我自己也踩了。**

```python
for f in asyncio.as_completed(future_map):        # ❌ f 不是原始 Task
    task_id = future_map[f]                       #    KeyError！

async for f in asyncio.as_completed(future_map):  # ✅ async 迭代才吐原始 Task
    task_id = future_map[f]                       #    能用
```

| 迭代方式 | 吐什么 |
|---|---|
| `for` | **awaitable**（包装过的，**不能当 dict 的 key**） |
| **`async for`** | **原始 Task**（能用 `future_map[f]` 反查身份） |

> **Day 27 的 `future_map[f]` 模式不能"照搬"** —— 线程池的 `as_completed` 吐的就是原始 `Future`，asyncio 的不是。

---

## 三、实测数据

`benchmark.py` —— 四组终极对比：

```
8 个任务 [3, 1, 4, 2, 1, 2, 3, 2]
串行总和 = 18s，最长任务 = 4s

asyncio 不限流       : 4.00s   （并发度 8）
asyncio Semaphore(3) : 7.00s   （并发度 3）

线程池(3)            : 7.01s   （并发度 3）
线程池(8)            : 4.01s   （并发度 8）
```

### ⭐ 请看这两组

```
并发度 = 3 ─┬─ asyncio + Semaphore(3) : 7.00s
            └─ 线程池(3)              : 7.01s     ← 差 0.01 秒

并发度 = 8 ─┬─ asyncio 不限流         : 4.00s
            └─ 线程池(8)              : 4.01s     ← 差 0.01 秒
```

**两种完全不同的机制，只要并发度一样，耗时几乎完全一样。**

**这也回答了那个问题**：

> **「线程池的 `max_workers` 和 asyncio 的 `Semaphore`，哪个更好？」**
>
> **不是"哪个更好" —— 它们控制的是同一件事（并发度）。**
> **选哪个取决于"任务怎么来的"**：一次性一批 → 信号量；源源不断 → 消费者。

### 三个参照数字

| 数字 | 含义 |
|---|---|
| **18s** = `sum(DUR)` | 串行（`limit=1` 时就是这个） |
| **4s** = `max(DUR)` | 并发度 ≥ 任务数时（被最长的卡住） |
| **7s** | 并发度 = 3 时的调度结果 |

### 「峰值并发」的直接测量（`ex3.py`）

```
① 不限流       : 4.00s   峰值并发 = 8
② Semaphore(3) : 7.00s   峰值并发 = 3
```

**`峰值并发 = 3` 是"限流真的生效了"的数字证据** —— 不用靠肉眼看排列模式去猜。

**计数技巧**：

```python
running += 1                        # 进来 +1
peak = max(peak, running)           # 刷新历史最高
await asyncio.sleep(seconds)        # ← 这道 await 就是"占用期"
running -= 1                        # 出去 -1
```

**为什么准**：`+1` 和 `peak = max(...)` 之间**没有 await** → 不可分割 → 不会被插队。
（中间插一个 `await` 就会像 Day 25 那个计数器一样丢数据：100 → 34。）

---

## 四、踩坑

### 🔴 1. `limited` 里 `return ai_task(...)` 少了 `await` —— **限流完全失效**

```python
    async def limited(ta, na, se, bo):
        async with sem:
            return ai_task(ta, na, se, bo)      # ❌ 返回协程对象，不执行
```

**三个连锁后果**：

| # | 后果 |
|---|---|
| a | **任务根本没执行** → `RuntimeWarning: coroutine 'ai_task' was never awaited` |
| b | ⚠️ **限流完全失效** —— `with` 块里没有 `await` → 块瞬间结束 → **名额立刻还回去** |
| c | `await f` 拿到的是**协程对象**，不是结果 —— 但它不是异常，所以 `try` 不进 `except` → **8 个全记成 success** |

**修法**：`return await ai_task(...)`

> **规矩**：**`async with` 保护的是"块里面的执行时间"。块里没有 `await` → 它什么都保护不了。**

### 🔴 2. 元组里的逗号写进了引号 —— **第三次踩「相邻字符串拼接」**

```python
("task_002,""jack",1,False)     # ❌ "task_002," 和 "jack" 被自动拼接
```

**实测解析结果**：`('task_002,jack', 1, False)` —— **元组少了一个元素** → 拆包失败。

**今天这一周踩了三次，三个不同方向**：

| 时候 | 写错的 | 错在 | 后果 |
|---|---|---|---|
| Day 27 S3 | `"Bob"" ,1` | **多**了一个引号 | `SyntaxError`（**报错在下一行**） |
| Day 27 主线 | `"TASK-004"	"Lucy"` | **少**了一个逗号 | `ValueError`（元组少一项） |
| Day 28 V2 | `"task_002,""jack"` | **逗号写进引号里** | `ValueError`（元组少一项） |

**共同根因**：**从表格/别处粘过来的，逗号和引号的边界没对齐。**

**防错三招**：

1. **把元组列表换成「字典列表」** —— 字段有名字，少写立刻 `KeyError`（清晰），而且**不会"自动拼接"**
   ```python
   TASKS = [{"id": "task_001", "name": "tom", "seconds": 3, "boom": False}, ...]
   ```
2. **加一行体检**：`assert len(row) == 4, f"这一行只有 {len(row)} 个：{row}"`
3. **一行一个、逗号对齐，别从表格粘**

### 🔴 3. `asyncio.as_completed` 用普通 `for` → `KeyError`

```
KeyError: <coroutine object _AsCompletedIterator._wait_for_one at 0x...>
```

**修法**：改成 `async for`（见上面 2.3）。

### 🟠 4. 热身题：三个错叠在一起

| # | 写错的 | 后果 |
|---|---|---|
| a | `asyncio.sleep(seconds)` 少了 `await` | **根本没睡** |
| b | `[await asyncio.create_task(...) for ...]` | **边建边等 → 串行**（L2 那个坑） |
| c | `asyncio.as_completed(results)` | 收到的是**结果字符串**，不是 Task → `TypeError` |

**b 和 c 的根因是同一个**：

```python
task = asyncio.create_task(coro)              # → 拿到 【Task 对象】
result = await asyncio.create_task(coro)      # → 拿到 【任务的返回值】
```

**要收集一批 Task 留给后面用 → 这一阶段绝对不能 `await`。**

### 🟠 5. `asyncio.as_completed` 用 `.result()` 取结果

```python
for f in asyncio.as_completed(tasks):
    print(f.result())          # ❌ AttributeError: 'coroutine' object has no attribute 'result'
    print(await f)             # ✅
```

**线程池版用 `.result()`，asyncio 版用 `await`** —— 同名的两个东西，行为不同。

---

## 五、还没搞懂的

1. 把 `limit` 换成 1 / 2 / 3 / 4 / 8 各跑一遍，**耗时分别是多少？**（先预测再跑）
2. `Semaphore` 的范围如果包得太宽（比如包住整个任务，而不只是调用下游那一句），会浪费多少并发度？
3. 真实场景里，如果任务数有 1000 个，`Semaphore(3)` 和「3 个消费者」哪个更省内存？（提示：思路是"造了多少个 Task"）
4. `asyncio.TaskGroup` 和 `Semaphore` 能一起用吗？它和 `gather` 在失败时行为不同，会影响限流吗？
