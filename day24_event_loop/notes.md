# Day 24 · 事件循环与 create_task

2026-09-23 · Python 3.13 · macOS · 数据都是本机跑出来的

今天真正搞明白的只有一件事：**创建任务**和**等待任务**不是同一回事。
之前我一直把它们当成一件事，所以今天卡了三次。

---

## 一、ex1：为什么是 1 秒不是 2 秒

```python
async def main():
    t0 = time.perf_counter()
    print("--- 创建两个任务 ---")
    t1 = asyncio.create_task(work("q", 1))
    t2 = asyncio.create_task(work("b", 1))
    print("--- 任务已创建，还没 await ---")
    await t1
    await t2
    print(f"总耗时：{time.perf_counter()-t0:.2f}s")
```

我原本以为要 2 秒 —— 昨天写 `await job("A")` 再接 `await job("B")`，就是两个 1 秒加起来。

实际跑出来：

```
--- 创建两个任务 ---
--- 任务已创建，还没 await ---
q:开始
b:开始
q:结束
b:结束
总耗时：1.00s
```

盯着看了半天才反应过来：**关键不在这两行 await，在上面那两行 create_task。**

注意「q:开始」的位置 —— 它在「任务已创建，还没 await」**后面**。
也就是说 `create_task` 只是把任务排进队列，并没有真的执行它。真正开跑，是 `main` 第一次让位的时候。

---

## 二、那到底是哪一个 await 启动的？

我一开始以为「必须是 await 那个任务，它才会启动」。所以专门试了一下：在 ex2 里插一句 `await asyncio.sleep(0)`。

```
刚创建时 done() = False
q:开始
让出一圈后 done() = False
过了 0.5 秒 done() = False
q:结束
await 之后 done() = True
t.result() = q的结果
拿到的 result = q的结果
```

「q:开始」正好出现在 `sleep(0)` 后面。

所以答案是：**任何一个让位点都会启动它，不是非得 await 那个任务本身。**
`sleep(0)` 就是「只让位、不多等」，用它纯粹是为了偷看一眼中间的 `done()`。

把 `sleep(0)` 删掉，「q:开始」会往下挪到 `await asyncio.sleep(0.5)` 后面 —— 这个我试过。

### 但这带出一个反直觉的结论

```python
t = asyncio.create_task(work("q", 1))
await t
```

跟直接写 `await work("q", 1)` 几乎没区别 —— 都是「创建 + 立刻等」，都是串行。
因为 `await t` 会一直等到任务结束，中间插不进任何 print。

**`create_task` 的价值，全在「创建」和「等待」之间那段空档里。** 空档里什么都不干，它就白写了。

---

## 三、今天卡的三次，答案其实是同一个

1. ex1 为什么是 1 秒不是 2 秒？
2. ex2 里任务为什么在 `sleep(0)` 就跑了，不应该在 `await t` 吗？
3. `run_all_first` 里 10 个任务是哪一刻一起启动的？

答案：

> **第一次让位的那一刻，队列里有几个任务，就有几个一起跑。**

对号入座：

| 场景 | 第一次让位时队列里有几个 | 结果 |
|---|---|---|
| ex1（两个 create_task 之后 await t1） | 2 个 | 1.00s |
| 昨天串行（`await job("A")` 再 `await job("B")`） | 1 个（B 还没被创建） | 3.00s |
| benchmark 的 run_all_first | 10 个 | 0.20s |
| benchmark 的 run_one_by_one | 1 个 | 2.01s |

还有个细节：**列表推导式不产生让位点。**

```python
tasks = [asyncio.create_task(work(i)) for i in range(n)]   # 这一行不让位
```

10 次 `create_task` 全在一个同步表达式里完成，一个都没跑起来。它们都在等第一次 `await`。

---

## 四、benchmark：同一个 API，两种写法，10 倍差距

```python
async def run_all_first(n):
    """先把 n 个任务全部点火，最后统一等"""
    t0 = time.perf_counter()
    tasks = [asyncio.create_task(work(i)) for i in range(n)]
    for t in tasks:
        await t
    return time.perf_counter() - t0


async def run_one_by_one(n):
    """每创建一个就立刻 await"""
    t0 = time.perf_counter()
    for i in range(n):
        t = asyncio.create_task(work(i))
        await t
    return time.perf_counter() - t0
```

实测：

```
N = 10，每个任务 0.2s，理论最优 0.2s

先全建再统一 await : 0.20s   加速比 9.99x
边建边 await（错）  : 2.01s   加速比 1.00x
asyncio.gather     : 0.20s   加速比 9.97x
```

最扎心的是中间那个。看上去很像并发（有 create_task、有 for 循环），实际是纯串行：

```python
for i in range(n):
    t = asyncio.create_task(work(i))
    await t          # ← 一创建就等它，等于没并发
```

它还比纯串行略慢（2.01s vs 2.00s）—— 大概是多付了 10 次创建 Task 的开销（也可能有测量波动）。

**结论：并发不看你调了几次 `create_task`，看第一次让位时队列里站着几个。**

---

## 五、手写一个事件循环（今天最值钱的 20 行）

ex4 里没有 `async`、没有 `await`，但它就是 asyncio 的核心。

```python
from collections import deque

def task_a():
    print("  A 第一步")
    yield "让位"          # ← 相当于 await
    print("  A 第二步")
    yield "让位"
    print("  A 第三步")

def task_b():
    print("  B 第一步")
    yield "让位"
    print("  B 第二步")

def run(*tasks):
    queue = deque(tasks)
    step = 0
    while queue:
        step += 1
        task = queue.popleft()
        try:
            print(f"[第 {step} 圈] 轮到 {task.__name__}")
            next(task)
            queue.append(task)          # 没跑完，放回队尾
        except StopIteration:
            print(f"[第 {step} 圈] {task.__name__} 结束")

run(task_a(), task_b())
```

实际输出：

```
=== 手写的最小事件循环 ===
[第 1 圈] 轮到 task_a
  A 第一步
[第 2 圈] 轮到 task_b
  B 第一步
[第 3 圈] 轮到 task_a
  A 第二步
[第 4 圈] 轮到 task_b
  B 第二步
[第 4 圈] task_b 结束
[第 5 圈] 轮到 task_a
  A 第三步
[第 5 圈] task_a 结束
```

几个自己看出来的点：

**① A 和 B 交替，就是单线程并发的全部秘密。**
没有别的东西 —— 一个 `while`、一个队列、轮流 `next()`。

**② 说好跑 6 圈，实际只跑了 5 圈。**
因为 `task_b` 的最后一次 `next()` 会直接抛 `StopIteration`：
「B 第二步」和「task_b 结束」挤在同一圈里，结束不需要额外占一轮。
（我直觉上以为「结束」要单独占一圈，是错的。）

**③ 这个手写版不知道「谁该醒了」。**
它只会傻转圈，谁在队首就推谁。asyncio 多出来的就是这块：
定时器（谁该在 0.2 秒后醒）+ I/O 就绪通知（哪个 socket 有数据了）。

**④ `yield` ≈ `await`**，共同点是「让位」。

对应关系：

| 手写版 | asyncio |
|---|---|
| `yield` | `await` |
| `deque` + `while` | 事件循环本体 |
| `next(task)` | 推进一个协程 |
| `queue.append(task)` | 任务重新排队，等下次被唤醒 |
| （没有） | 定时器 / I/O 就绪通知 |

---

## 六、顺手解掉一个更底层的问题：await 为什么能拿到 return 的值

`return` 的值不是「返回」给谁的 —— 它是**装在 `StopIteration` 里被送出来的**。

生成器早就演示过这件事：

```python
def gen():
    yield 1
    return 42

g = gen()
next(g)      # 1
next(g)      # 抛 StopIteration，42 挂在 e.value 上
```

实测：

```
第一次 next()： 1
第二次 next() 抛了 StopIteration
  e.value = 42
```

协程也一样。手动驱动一下就能看见：

```
协程跑完了，StopIteration.value = '协程的返回值'
```

因为 `await X` 本质上 ≈ `yield from X.__await__()`，而 `yield from` 能从子生成器拿到返回值，
靠的就是捕获 `StopIteration` 再取 `.value`。所以 `await` 拿到 return 值是同一套机制。

语言为什么非得这么设计：普通函数能 `return`，是因为**调用者一直站在栈上等着接**。
协程没有这个「一直站着的上一帧」—— 它可以被挂起，期间事件循环去跑别的任务了。
值没法顺着栈回来，就只能搭着「我结束了」这个信号一起出来。

**所以在协程里，「结束」和「返回值」是同一个信号。**

顺带解释了一个小规则：`await 42` 为什么报 TypeError —— 数字没有「被驱动到结束」的过程，没货可接。

三个门牌号，其实是同一个东西：

| 层面 | 写法 |
|---|---|
| 机制层 | `StopIteration.value` |
| 对象层 | `task.result()` |
| 语法层 | `await task` 的求值结果 |

---

## 七、踩坑

1. **`create_task` 之后不 await** → 任务永远不会跑 → `Task was destroyed but it is pending!`
2. **`create_task` 的返回值不存进变量** → 事件循环对 Task 只持**弱引用**，可能被 GC 掉，任务中途无声消失
3. **任务还没完成就调 `t.result()`** → `InvalidStateError`
4. **对「不启动」的误解 ⚠️**：裸调用协程（`work("q", 1)` 不 await）**不会卡住程序、不会报错、退出码 0**，
   只会有一句 `RuntimeWarning: coroutine ... was never awaited`。它完全不影响程序运行，所以最难发现。
5. 全角引号 → `dquote>` 卡住（`Ctrl+C` 退出）


