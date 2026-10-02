# Day 29 · 调度器 V3（生产级）

2026-10-01 ~ 10-02 · Python 3.13 · macOS · 下面的输出都是本机实测

> **今天给 V2 加了四样东西**：`timeout` / `retry` / `to_thread` / 结果落盘。
>
> **"生产级"的含义不是代码更复杂，而是：把「出错」当成正常情况来设计。**

---

## 一、成品

`day29_scheduler_v3/scheduler_v3.py` —— `Semaphore(3)` + 单次超时 + 重试 + 指数退避 + JSON 落盘。

**实测输出**：

```
TASK-002 | jack  | success | 试了 1 次
TASK-005 | bob   | success | 试了 1 次
  重试 TASK-003：ValueError rose 服务端错误 → 等 0.1s 后第 2 次
  重试 TASK-003：ValueError rose 服务端错误 → 等 0.2s 后第 3 次
TASK-003 | rose  | failed  | 试了 3 次 | rose 服务端错误
  重试 TASK-006：ValueError amy 第 1 次尝试失败 → 等 0.1s 后第 2 次
  重试 TASK-006：ValueError amy 第 2 次尝试失败 → 等 0.2s 后第 3 次
TASK-006 | amy   | success | 试了 3 次
TASK-001 | tom   | success | 试了 1 次
TASK-004 | lucy  | success | 试了 1 次
TASK-008 | zoe   | success | 试了 1 次
  重试 TASK-007：TimeoutError 超过 4.0s → 等 0.1s 后第 2 次
  重试 TASK-007：TimeoutError 超过 4.0s → 等 0.2s 后第 3 次
TASK-007 | ken   | failed  | 试了 3 次 | 连续 3 次都超过 4.0s

成功 6 / 失败 2   总耗时 15.21s
结果已写入 results.json（8 项）
```

**`results.json`（片段）**：

```json
{
  "TASK-003": {
    "name": "rose",
    "status": "failed",
    "attempts": 3,
    "error": "ValueError: rose 服务端错误"
  },
  "TASK-007": {
    "name": "ken",
    "status": "failed",
    "attempts": 3,
    "error": "TimeoutError: 连续 3 次都超过 4.0s"
  }
}
```

---

## 二、四个知识点

### 1. `timeout` —— 给单个任务加超时

```python
result = await asyncio.wait_for(coro, timeout=2)      # 包【一个协程】

async with asyncio.timeout(2):                        # 包【一整块代码】（3.11+）
    await step1()
    await step2()
```

**⭐ 最关键的行为：超时后原任务会被【取消】**

**`ex2.py` 实测**：

```
① wait_for 超时：
    A 开始（要睡 5s）
    → TimeoutError，实际耗时 0.30s

② 超时之后，那个任务还在跑吗？
    B 开始（要睡 5s）
    task.cancelled() = True
    task.done()      = True
    await task → CancelledError（被取消了，不是「还在跑」）

③ shield 保护：外层超时，内层继续跑
    C 开始（要睡 0.6s）
    → 外层在 0.20s 就超时了
    C 结束
    但内层还在跑 → 最终结果：C 完成
```

**看输出的诀窍**：**被超时掐掉的任务，只有「开始」没有「结束」。**
（`A 开始` 出来了，`A 结束` 永远不打印 —— 因为 `await asyncio.sleep(5)` 那一行被从中间打断了。）

**两种写法的分工**：

| | `wait_for(coro, timeout)` | `async with asyncio.timeout(s)` |
|---|---|---|
| 包什么 | **一个协程** | **一整块代码** |
| 超时从哪算 | 那一次调用 | **进入 `async with` 开始算** |
| 适合 | "**这一次请求**最多等 2 秒" | "**这个流程**总共最多 5 秒" |

> **多步流程必须用 `asyncio.timeout`** —— 用两个 `wait_for` 是"每步各 2 秒"（可能拖到 4 秒），
> 而 `async with` 才是"**总预算 2 秒**"。

### 2. `retry` —— 失败自动重试

**三个必须设计的点**：

| # | 设计 | 为什么 |
|---|---|---|
| 1 | **最多重试几次** | 不然可能无限重试，把下游打死 |
| 2 | **每次等多久 → 指数退避** | **避免"重试雪崩"**：所有失败任务同时重试 = 同时给下游一波新压力 |
| 3 | ⭐ **哪些错误该重试** | 见下表 |

| 该重试 | 不该重试 |
|---|---|
| 超时 `TimeoutError` | `400` 参数错 |
| 连接失败 `ConnectionError` | `401` 没认证 / `403` 没权限 |
| `429` 限流 | `404` 资源不存在 |
| `500` / `502` / `503` 下游临时故障 | **参数类错误 —— 重试一万次也一样** |

**`ex3.py` 实测**：

```
A) 前 2 次失败、第 3 次成功：
    重试 A：第 1 次尝试失败 → 等 0.1s 后第 2 次
    重试 A：第 2 次尝试失败 → 等 0.2s 后第 3 次
   最终：✅ 第 3 次成功（共试了 3 次）

B) 每次都失败（重试 3 次后放弃）：
    重试 B：第 1 次尝试失败 → 等 0.1s 后第 2 次
    重试 B：第 2 次尝试失败 → 等 0.2s 后第 3 次
    重试 B：第 3 次尝试失败 → 等 0.4s 后第 4 次
   最终：❌ 第 4 次尝试失败（共试了 4 次）
```

**重试循环的核心只有 8 行**：

```python
    for i in range(MAX_RETRY + 1):              # 试 MAX_RETRY+1 次
        try:
            return await 任务()
        except 可重试的错误 as e:
            if i == MAX_RETRY:                  # 最后一次，放弃
                raise
            await asyncio.sleep(BASE * (2 ** i))   # 指数退避
```

**⚠️ `MAX_RETRY` 和「尝试次数」差 1**：
`MAX_RETRY = 2` → 总尝试次数 = **1 次首试 + 2 次重试 = 3 次** → `range(MAX_RETRY + 1)`。

**⚠️ 是 `2 ** i`（2 的 i 次方），不是 `i ** 2`（i 的平方）**：

| `i` | `0.1 * i**2` | `0.1 * 2**i` |
|---|---|---|
| **0** | **0.0** ← 不等待！ | **0.1** |
| 1 | 0.1 | 0.2 |
| 2 | 0.4 | 0.4 |

`i**2` 在 `i=0` 时是 **0** —— **第一次重试完全不等待，退避就没意义了。**

### 3. `asyncio.to_thread` —— 调用只有同步版的老库

```python
result = await asyncio.to_thread(blocking_func, arg1, arg2)
```

**问题**：在协程里直接调同步阻塞函数（老库的 `requests.get`、`time.sleep`、文件读写）
→ **按住整个事件循环** → 别的协程全得干等 → **你以为在并发，其实退化成串行，而且看不出来**。

**解法**：`to_thread` 把它丢进**线程池**跑，事件循环立刻腾出来。

**老写法（3.9 之前）**：`await loop.run_in_executor(None, func, *args)`

**`ex4.py` 实测（用心跳 ♥ 当证据）**：

```
  ❌ 直接调同步函数：
♥0.1 ♥0.2
      ↑ 两个阻塞函数共 1.01s —— 这期间心跳【一个都没打】

  ✅ to_thread（丢进线程池）：
♥0.1 ♥0.2 ♥0.3 ♥0.4 ♥0.5 ♥0.6 ♥0.7
      ↑ 两个 0.5s 共 0.51s（真并发）—— 心跳【一直在跳】
```

> **心跳（heartbeat）是个通用技巧**：
> 想证明"事件循环还活着 / 被卡住了"，就开一个每 0.1 秒打点的协程。
> **它停了 = 循环被按住了。**

### 4. 结果落盘 —— JSON

```python
import json

with open("results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

with open("results.json", encoding="utf-8") as f:
    results = json.load(f)
```

**两个参数都重要**（实测）：

```
默认 ensure_ascii=True  :  "error": "rose \u6267\u884c\u5931\u8d25"    ← 中文被转义，没法看
ensure_ascii=False      :  "error": "rose 执行失败"                   ← ✅
加 indent=2             :  缩进换行，人能读
```

**为什么要落盘**：程序崩了不丢数据 / 能断点续跑 / 能事后分析。

---

## 三、实测数据

### `benchmark.py` —— 不重试 vs 重试（今天最有说服力的一张表）

```
8 个任务，每个 1s；第 3 和第 6 个「前 2 次会失败」

不重试（max_retry=0）: 成功 6 / 失败 2   耗时 1.00s   总请求次数 8
重试（max_retry=3）  : 成功 8 / 失败 0   耗时 3.31s   总请求次数 12
```

| | 不重试 | 重试 | 变化 |
|---|---|---|---|
| **成功率** | 6/8 = 75% | **8/8 = 100%** | ⬆️ 收益 |
| **耗时** | 1.00s | **3.31s** | ⬆️ **3.3 倍** |
| **对下游请求量** | 8 次 | **12 次** | ⬆️ **+50%** |

> ### 重试不是免费的
> 把成功率从 75% 拉到 100%，代价是 **3.3 倍耗时 + 对下游多 50% 的压力**。
>
> **所以"重试几次"是业务决策**：
> - 用户在等（网页请求）→ 重试要**少、快**
> - 后台批量任务 → 可以**多试几次**
> - 下游已经快挂了 → **重试会加速它死亡**

---

## 四、踩坑

### ⚠️ 1. `timeout` 阈值卡在边界上 → **正常任务被误杀**

第一版我写 `TIMEOUT = 3.0`，而 `tom` 正好睡 3 秒：

```
TASK-001 | tom | failed | 试了 4 次 |        ← ❌ 正常任务被判超时
成功 5 / 失败 3
```

**`wait_for(sleep(3), timeout=3)` 是"刚好不够"** —— 调度和事件循环都有微小开销，**卡在边界上必然误判**。

> **规矩：超时阈值必须留余量。** 正常最长 3 秒 → 超时设 **4 或 5 秒**。
>
> **这个坑在线上很致命**：一个正常的慢请求被判超时 → 触发重试 → **对下游的请求量凭空翻倍**。
>
> **"超时设多少"要看 P99 延迟数据，不能拍脑袋。**

### ⚠️ 2. ⭐ `per-attempt timeout` 会被重试"乘出来"

**看那 15.21 秒**：

| 任务 | 耗时 | 说明 |
|---|---|---|
| **TASK-007 ken** | **12.3s** | **3 次尝试 × 4 秒超时 + 0.3 秒退避** |
| 其他 7 个 | 各 ≤ 3s | 3 个名额并行，很快就完了 |
| **总耗时** | **15.21s** | **ken 一个人占了 80%** |

**你设的是"4 秒超时"，实际变成了"12 秒不许超时"**：

```
一个卡死的任务 × 3 次尝试 × 4 秒超时 = 12 秒白等
```

**两种生产修法**：

| 修法 | 怎么做 |
|---|---|
| **① 给整个任务设总预算** | `async with asyncio.timeout(6)` 包住**整个重试循环** —— "含所有重试，最多 6 秒" |
| **② 对超时的重试更保守** | 超时只重试 1 次，服务端错误才重试 3 次（**超时的任务多半还会超时**） |

> **这就是 `asyncio.timeout`（包一整块）比 `wait_for`（包一个调用）更重要的原因** ——
> **它是"总预算"，不会被循环乘出来。**

### ⚠️ 3. `TimeoutError` **没有消息** —— 日志会空半行

`asyncio.wait_for` 超时时抛的 `TimeoutError`，`str(e)` 是**空字符串**：

```
TASK-007 | ken | failed | 试了 3 次 |          ← 修之前：后面什么都没有
```

**生产级的日志不该出现"空了半行"。** 修法：

```python
            if i == MAX_RETRY:
                if isinstance(e, TimeoutError):
                    raise TimeoutError(f"连续 {MAX_RETRY + 1} 次都超过 {TIMEOUT}s") from e
                raise
```

**（`from e` 保留原始错误链 —— 排查时能看到底层到底出了什么事。）**

### ⚠️ 4. 自己写 V3 时踩的 5 个错（剥洋葱）

一次只暴露一个，修完一个立刻撞下一个：

| # | 写错的 | 报错 |
|---|---|---|
| **1** | `attempts.get[task_id,0]` —— **方括号写成圆括号** | `TypeError: 'builtin_function_or_method' object is not subscriptable` |
| **2** | `type(e).__namee__` —— **多写了个 e** | `AttributeError: ... has no attribute '__namee__'` |
| **3** | `raise f"连续3次失败"` —— **raise 了一个字符串** | `TypeError: exceptions must derive from BaseException` |
| **4** | `RETRY_BASE*(i**2)` —— **平方 ≠ 指数退避** | 不报错，但 `i=0` 时 delay=0 |
| **5** | `dec = ...` 拼好了**却没用进 print** | 不报错，但日志里看不出错误类型 |

**外加一个藏起来的**：`attempts.get[task_id,o]` 里的 `o` 是**字母 o**，不是数字 `0` → `NameError`。

**三个教训**：

1. **报错一次只显示一个** —— 有 5 个错，只看到第 1 个。**修完撞下一个是常态。**
2. **拼写错误占一半** → **用 VS Code 补全，别硬敲长名字**（`rusult` / `squaer` / `succes` / `arm` / `o` / `__namee__`）
3. **「算了但没用」这一族又出现了** → **写完一个变量，问"它在哪一行被用到？"**

### ⚠️ 5. 运行时的工作目录要注意

```python
with open("results.json", "w") as f:      # ← 相对路径 = 【当前工作目录】
```

**从哪个目录跑，文件就写到哪。** 跑之前先 `cd` 到 `day29_scheduler_v3/`，
不然 `results.json` 会落在你没想到的地方。

---

## 五、还没搞懂的

1. 给整个重试循环加 `async with asyncio.timeout(6)` 之后，`ken` 会从 12.3s 降到多少？（先预测再跑）
2. `asyncio.timeout` 抛的也是 `TimeoutError`，和 `wait_for` 抛的**分不清** —— 那嵌套使用时怎么区分是我超时还是任务超时？
3. 重试的等待时间（`RETRY_BASE`）如果调大 10 倍，成功率会变吗？耗时变多少？
4. 哪些错误"不该重试"？如果我的代码无条件重试 `400 参数错误`，会发生什么？
