# ai-learning

> 转行 AI 应用开发的学习记录。每天 4 小时，按「学 → 理 → 懂 → 存」四步走，**当天代码当天提交**。

**当前进度：Day 24 / 约 160 天** · Python · 并发模型 · asyncio ·（后续）FastAPI · RAG 应用开发

---

## 这是什么

不是一个「跟教程敲一遍」的仓库。**每个目录 = 一天的完整产出**：

| 产物 | 说明 |
|---|---|
| `*.py` | 当天自己敲的、能跑的代码（不是复制的） |
| `notes.md` | 当天整理的概念 / 踩坑 / **实测数据** |

**所有性能数据都来自本机实测**，不是从文章里抄的。跑出来的数字和预期不符时，以数字为准。

环境：macOS (Apple Silicon) · Python 3.13 · uv

---

## 学习进度

| 天 | 主题 | 产出 | 状态 |
|---|---|---|---|
| Day 21 | Git 与开发环境 | 工作区/暂存区/版本库三区模型、SSH 免密推送 | ✅ |
| Day 22 | 进程与线程并发模型 | GIL、线程池 vs 进程池对比实验 | ✅ |
| Day 23 | 协程与 asyncio | `async`/`await`、事件循环、`gather`、阻塞实验 | ✅ |
| Day 24 | 事件循环与 `create_task` | — | 🔄 |

---

## 实测数据

### Day 22 · CPU 密集（4 个计算任务）

| N | 串行 | 线程池 | 进程池 |
|---|---|---|---|
| 20 万 | 0.02s | 1.07x | **0.31x** |
| 200 万 | 0.21s | 1.25x | 1.92x |
| 2000 万 | 1.86s | 1.11x | 3.49x |
| 6000 万 | 5.62s | 1.09x | 3.46x |

### Day 22 · I/O 密集（4 个任务各等 1 秒）

| 串行 | 线程池 | 进程池 |
|---|---|---|
| 4.02s | **3.99x** | 3.67x |

### Day 23 · 纯等待任务（N = 10，每个 0.2s）

| 方式 | 耗时 | 加速比 |
|---|---|---|
| 串行 `await` | 2.01s | 1.00x（基准） |
| `asyncio.gather` | 0.20s | **10.01x** |
| `gather` + `time.sleep` | 2.04s | **0.99x** |

---

## 自己总结的几条结论

**① 线程池做计算永远 ≈ 1.1x**
从 20 万到 6000 万一条平线 —— GIL 的影响与任务大小完全无关。

**② 进程池收益随任务变大而上升**
0.31x → 3.49x。启动开销是固定的，任务越大占比越小。

**③ asyncio 的加速比上限 = 任务数 N**
纯等待任务下，N=10 就是 10.01x，已经顶格。想要更高只能加任务数。

**④ 并发需要同时满足两个条件**
任务会**让位**（`await` 真正的 I/O）**且**同一时刻**有多个任务在等**。
所以 `gather` + `time.sleep` 是 0.99x：外壳是并发的，内核不让位，等于没并发，**开销全付、收益为零**。

**⑤ 变量不同的实验不能比大小**
Day 22 的 3.99x（4 个任务）和 Day 23 的 10.01x（10 个任务）**都跑满了各自的上限**，机制上没有优劣之分。

---

## 目录结构

```
day22_concurrency/        GIL、线程池 vs 进程池
├── learn_api.py          例 1：ThreadPoolExecutor + map
├── ex2.py ~ ex4.py       例 2-4：submit/Future/as_completed、ProcessPoolExecutor
├── benchmark.py          对比实验
└── notes.md
day23_asyncio/            协程、事件循环、asyncio
├── ex1.py                协程对象 vs 普通函数
├── ex2.py                await 是串行
├── ex3.py                asyncio.gather 并发
├── ex4.py                asyncio.sleep vs time.sleep
├── benchmark.py          三组控制变量对照
└── notes.md
```

---

## 怎么跑

```bash
git clone git@github.com:xu-wanhong/ai-learning.git
cd ai-learning
uv sync                          # 创建 .venv 并安装依赖

cd day23_asyncio
python benchmark.py              # 约 4.2 秒
```

---

## 学习计划

总周期 7–7.5 个月，每天 4 小时 × 每周 6 天。路线：

```
Python 进阶 → 网络/数据库 → FastAPI 后端 → RAG 应用开发 → 部署与工程化
```

第 3 个月末完成第一个 RAG 项目后开始投递。目标岗位：中小公司 / 传统行业数字化部门 / 外包与实施。
