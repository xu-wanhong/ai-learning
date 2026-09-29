# Day 27 · AI 任务调度器 V1

2026-09-26 ~ 09-29 · Python 3.13 · macOS · 下面的输出都是本机实测

今天第一次做「**作品**」，不是做「例子」。

**把 Day 22（线程池 / `Future` / `as_completed`）和 Day 25–26 的东西，拼成了一个能拿出去说的程序。**

---

## 一、成品

`day27_scheduler/scheduler.py` —— 用线程池调度 8 个模拟 AI 任务，其中 2 个会失败。

**实测输出**：

```
TASK-001 开始执行
TASK-002 开始执行
TASK-003 开始执行
TASK-002 执行结束
TASK-004 开始执行
TASK-002 | Jack  | success
TASK-001 执行结束
TASK-005 开始执行
TASK-001 | Tom   | success
TASK-004 执行结束
TASK-006 开始执行
TASK-004 | Lucy  | success
TASK-005 执行结束
TASK-007 开始执行
TASK-005 | Bob   | success
TASK-008 开始执行
TASK-003 | Rose  | failed  | Rose 执行失败
TASK-006 | Amy   | failed  | Amy 执行失败
TASK-008 执行结束
TASK-008 | Zoe   | success
TASK-007 执行结束
TASK-007 | Ken   | success

成功 6 / 失败 2   总耗时 7.01s
```

**读这段输出的三件事**：

1. **前 3 行「开始执行」连着出来** —— 3 个工人同时开跑
2. **结果按完成顺序**（先 1 秒的 Jack，最后 4 秒的 Rose）
3. **失败的 Rose 没有「执行结束」** —— 异常在 `sleep` 之后抛出，`print("执行结束")` 那行没走到

---

## 二、三个核心概念

### 1. ⭐ `future_map` 为什么必须有

```python
future_map[ex.submit(ai_task, tid, name, seconds, boom)] = (tid, name)
...
task_id, name = future_map[f]
```

**因为 `as_completed` 只给你 `Future`，它不告诉你这是哪个任务。**

`Future` 身上**没有任何业务信息** —— 没有 id、没有名字。所以必须**在提交的那一刻**自己记一笔。

**为什么存元组 `(tid, name)` 而不是只存 `tid`？** 因为最后的状态表两个都要用：

```python
results[task_id] = {"name": name, "status": "success", ...}
```

### 2. `result()` 把异常「重新抛出来」

任务是在**子线程**里跑的，异常没法直接传到主线程。所以：

```
子线程:  raise ValueError(...)
            ↓ 被 concurrent.futures 捕获
Future:  【寄存】起来
            ↓
主线程:  f.result()  →  把寄存的异常【重新抛出来】
```

**两个方法，行为相反**：

| 方法 | 行为 |
|---|---|
| `f.result()` | **抛出**寄存的异常 |
| `f.exception()` | **返回**异常对象（不抛） |

**注意**：崩的是 `f.result()` 那一行，**不是任务失败的那一刻** —— 中间隔着「寄存」。

### 3. 一个任务失败，不影响其他

**实测证据**：`成功 6 / 失败 2`，总耗时 **7.01s** —— 两个失败的任务**完全没有拖累**其他任务。

**这也是为什么 AI 应用必须用 `submit` + `as_completed` 而不是 `map`**：

| | 一个任务失败时 |
|---|---|
| `map` | **中断迭代**，后续结果全丢 |
| `submit` + `as_completed` | **隔离**，其他照常返回 |

---

## 三、实测数据

| 项 | 数值 |
|---|---|
| 任务数 | 8 |
| 工人数 | 3 |
| 所有任务耗时之和 | 18s（3+1+4+2+1+2+3+2） |
| 最长单个任务 | 4s |
| **实测总耗时** | **7.01s** |
| 成功 / 失败 | **6 / 2** |

**这三个数字的关系很重要**：

```
总耗时 ≥ 最长的那个任务      (4s)   ← 再多工人也快不过它
总耗时 ≤ 所有任务之和        (18s)  ← 再少工人也不会更慢
实测                        7.01s  ← 3 个工人调度出来的真实值
```

**和 Day 27 benchmark 的理论值完全一致**（benchmark 里「工人数 = 3」也是 7.01s）—— 说明调度和理论吻合，没有退化。

---

## 四、踩坑（今天是最厚的一节）

今天的 bug 一共 **17 个**。按危险程度分四类：

### 🔴 A 类 · 静默错误（**不报错，结果全错**）—— 最危险

| # | 坑 | 后果 |
|---|---|---|
| 1 | **`ValueError(...)` 少了 `raise`** | 只是创建了异常对象然后扔掉 → **该失败的任务正常返回了**，一个警告都没有 |
| 2 | **`success =+ 1` 写成了 `=+`** | `=+` 是"赋值成正 1"，不是累加 → 跑完 4 个任务 `success = 1` |
| 3 | **`except` 里引用了只在 `try` 里赋值的变量** | `f.result()` 抛异常 → 那个变量没赋值 → except 里用的是**上一轮的旧值**（静默打错），或者首次就是 `NameError` |
| 4 | **`f"结束(name)"`** —— 花括号写成了圆括号 | 打印出字面的 `结束(name)` |
| 5 | **`"开始{name}"`** —— 漏了 `f` 前缀 | 打印出字面的 `开始{name}` |
| 6 | **`"TASK-004"	"Lucy"`** —— 少写逗号 | 相邻字符串**自动拼接**成 `"TASK-004Lucy"` → 元组少一个元素 |
| 7 | **`future_map` 只存了 `name`** | 状态表需要 `task_id` 和 `name` 两个，只存一个后面要返工 |
| 8 | **`if __name__ == "__main__":` 只包住一部分** | **子进程会重新 import 主模块**，把没包住的模块级代码全部重跑一遍 |

> **A 类占了今天的一半。** 它们的共同点：**语法合法、程序跑完、退出码 0、结果错。**
> **第 1 条（少 `raise`）和第 2 条（`=+`）是我踩过最隐蔽的两个。**

**第 8 条的实测证据**（T5 那题）：进程池只包了最后一段，结果 4 个子进程各把「串行 4 次 + 线程 4 次」重跑了一遍 → 输出 66 行，进程池耗时 5.48s（真实值 0.65s）。**结论完全反了。**

**修法**：把**全部逻辑**塞进 `main()`，`if __name__ == "__main__": main()`。

### 🟡 B 类 · 语法错误（报错，但**位置误导**）

| # | 坑 | 报错 |
|---|---|---|
| 9 | `"Bob"" ,1` —— 多了一个引号 | `SyntaxError: leading zeros...` ← **箭头指向下一行的 `TASK-006`** |
| 10 | `boom=` —— 关键字参数没给值 | `SyntaxError: expected argument value expression` |
| 11 | 3 元组和 4 元组混着放 | `ValueError: not enough values to unpack (expected 4, got 3)` |

> **心法：报 `SyntaxError` 时，往回看一两行。** 引号、括号这类"配对符号"出错，报错位置常常差好几行。

### 🟠 C 类 · API 用错（报错，但要花时间想）

| # | 坑 | 后果 |
|---|---|---|
| 12 | `ex.done()` | `done()` 是 **`Future`** 的方法，不是 `Executor` 的。Executor 只有 `map` / `submit` / `shutdown` |
| 13 | `create_task(生成器表达式)` | `create_task` 收**一个**协程，`gather` 才收**一批** |
| 14 | `gather(生成器)` 少了 `*` | `unhashable type: 'list'` —— 报错完全看不出是少了星号 |
| 15 | `asyncio.as_completed` 用 `t.result()` | **asyncio 版吐的是 awaitable**，必须 `await t`；线程池版才是 `.result()` |
| 16 | `as_completed` 没加 `asyncio.` 前缀 | `NameError` —— **同名的两个东西**：`concurrent.futures.as_completed` / `asyncio.as_completed` |
| 17 | `def sum(num)` 覆盖内置 `sum` | 文件里再想用内置 `sum` → `TypeError` |

### ⚪ D 类 · 拼写

| # | 坑 |
|---|---|
| 18 | `rusult` → `result` |
| 19 | `squaer` → `square` |
| 20 | `succes` → `success` |

> **D 类一跑就报错，最好查。** 但**会浪费时间** —— **用 VS Code 的补全，别硬敲长单词**。

---

## 五、几个值得单独记的结论

### 1. 「能跑」不等于「对」

```python
def sum(num):       # 覆盖了内置 sum
    ...
```
能跑、不报错 —— **但这个名字不能用了**。
```python
ValueError(...)     # 少了 raise
```
能跑、不报错 —— **但该失败的任务没失败**。

### 2. `try` 的范围要"刚好"

```python
for f in as_completed(future_map):
    task_id, name = future_map[f]      # ← 放 try 外面
    try:
        result = f.result()            # ← 只包这一句
        ...
    except ValueError as e:
        ...                            # ← 只用 name / e，别碰 result
```

**两个原则**：
- **`except` 块里要用到的东西，必须在 `try` 之前准备好**（否则 `NameError`）
- **也只包"可能因为外部原因失败"的那一句** —— 包太宽会把"自己代码的 bug"和"任务的失败"混在一起

### 3. 报错是一次一个的（剥洋葱）

`S3` 那题我一次写了 3 个错，Python 只报第 1 个。**修完立刻撞第 2 个，再修再撞第 3 个。**

**这是常态，不是"我怎么又错了"。**

### 4. 列表里的元素结构要统一

`("TASK-001", "tom", 3)` 和 `("TASK-003", "rose", 4, True)` 混着放 → 拆包必炸。

**统一成 4 元组**，不需要的写 `False`。

---

## 六、还没搞懂的

1. `f.exception()` 和 `f.result()` 各适合什么场景？（什么时候该"检查"而不是"取"）
2. 8 个任务、3 个工人的 7.01s 是怎么算出来的？能不能自己推一遍（而不是只看结果）
3. 如果任务数从 8 减到 4，总耗时会变成多少？（先预测再跑）
4. `ThreadPoolExecutor` 的工人数和 CPU 核数有关系吗？（还是纯 I/O 场景可以随便开）
