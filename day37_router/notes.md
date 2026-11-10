# Day 37 · FastAPI 项目结构 + 异步任务

2026-11-10 · macOS · FastAPI 0.162.0

> **Day 35–36 所有代码都在一个 `app.py` 里。今天把它拆开，并把"提交任务→查进度"跑通。**
>
> **一句话目标：你写的东西从"练习"变成"服务"。**

---

## 一、为什么不能全塞一个文件

**Day 36 的 `app.py` 已经 100 多行、5 个接口。真实的项目**：

```
接口 30 个 + 数据模型 20 个 + 数据库操作 + 业务逻辑 + 工具函数
→ 3000 行的 app.py
```

| 问题 | 后果 |
|---|---|
| **找不到东西** | 想改"任务相关"的代码，得全文搜索 |
| **改 A 崩 B** | 一个文件里所有东西互相影响 |
| **没法拆活** | 两个人没法同时改不同功能（git 冲突） |

---

## 二、目录结构

```
day37_router/
├── .gitignore
├── app/
│   ├── __init__.py          ← 空文件，告诉 Python "app 是个包"
│   ├── main.py              ← 入口：创建 app，挂路由
│   ├── models.py            ← 所有 Pydantic 模型
│   └── routers/
│       ├── __init__.py      ← 空文件
│       └── tasks.py         ← 任务相关的接口
```

| 文件 | 装什么 | 什么时候改 |
|---|---|---|
| **`main.py`** | **只有"接线"**（创建 app、挂路由） | 很少 |
| **`models.py`** | 请求 / 响应的"长什么样" | 改字段时 |
| **`routers/tasks.py`** | **任务相关的全部接口** | 加接口时 |

> **以后加功能 → 加一个新 router，`main.py` 只多一行 `include_router`.**
>
> **`__init__.py` 是空文件但必须有** —— 它告诉 Python "这个文件夹可以当包来 import".

---

## 三、`APIRouter` —— 拆路由

### 打电话的比方

| 代码 | 比方 |
|---|---|
| `app = FastAPI()` | **总机**（所有请求先到这儿） |
| `router = APIRouter()` | **分机**（可以单独拎出来搬走的小 app） |
| **`app.include_router(router)`** | **"这个分机接到总机上"** |

### 三个参数

```python
router = APIRouter(prefix="/tasks", tags=["任务"])
```

| 参数 | 作用 | 不写会怎样 |
|---|---|---|
| **`prefix="/tasks"`** | 这个分机里所有路径**自动加前缀** | 每个接口都得写全 `/tasks/xxx` |
| **`tags=["任务"]`** | **`/docs` 里按标签分组** | 所有接口挤在一堆 |
| **`response_model=Xxx`**（每个接口上） | 声明返回结构 | 文档里不显示返回示例 |

### ⚠️ `prefix` 拼接规则

```python
prefix = "/tasks"

@router.post("")           →  /tasks            ✅
@router.get("")            →  /tasks            ✅
@router.get("/{task_id}")  →  /tasks/{task_id}  ✅

@router.get("/")           →  /tasks/           ← 多了个斜杠！访问 /tasks 会 404
```

> **`prefix` 和 `path` 直接拼接** —— 所以根接口写 `""` 不写 `"/"`。

### `main.py` 只有 8 行

```python
from fastapi import FastAPI
from app.routers import tasks

app = FastAPI(title="Day 37 · 任务调度服务")

app.include_router(tasks.router)


@app.get("/health", tags=["系统"])
def health():
    return {"status": "ok"}
```

> **`/health` 是"我还活着"接口** —— 部署后监控系统定时调它，看服务有没有挂。

---

## 四、`models.py` —— 只描述"长什么样"

```python
class TaskRequest(BaseModel):                        # 提交时，你发什么
    name: str = Field(description="任务名")
    seconds: float = Field(default=1.0, ge=0.1, le=30)
    boom: bool = Field(default=False)


class TaskInfo(BaseModel):                           # 查询时，你会收到什么
    task_id: str
    name: str
    status: str
    seconds: float
    result: str | None = None
    error: str | None = None
```

**这个文件里没有一行逻辑**，只是"填表格的模板"。

**`str | None = None`** 读作：**"要么是文字，要么是空（null）"**。

---

## 五、⭐ `BackgroundTasks` —— 提交**立刻**返回

### 问题

**任务要跑 3 秒。同步跑，接口就要等 3 秒。**

**这在真实场景不可接受**（AI 任务可能跑 30 秒）。

### 解法（三行）

```python
def create_task(req: TaskRequest, bg: BackgroundTasks):     # ① 参数里声明
    ...
    bg.add_task(run_task, task_id, req)                     # ② 挂到待跑队列
    return TASKS[task_id]                                    # ③ 立刻返回
```

### `bg.add_task(函数, 参数...)` 读法

```python
bg.add_task(run_task, task_id, req)
#            └──┬───┘  └──┬──┘ └─┬─┘
#          要跑的函数   参数1   参数2
```

**翻译**：**"等我把响应发出去，你在后台帮我调 `run_task(task_id, req)`。"**

### ⚠️ 最容易错的地方

```python
bg.add_task(run_task, task_id, req)      # ✅ 传【函数本身】（不加括号）
bg.add_task(run_task(task_id, req))      # ❌ 【现在】就执行了，然后传返回值
```

### 实测证据

```
① 提交任务 → 耗时 0.04 秒（任务要跑 3 秒，但响应不等它）
② 0.5 秒后查 → status: running
③ 4 秒后查   → status: success, result: "tom 执行成功（耗时 3.0s）"
```

> **状态流转**：`pending` → `running` → `success`
> 　　　　　　　　　　　　　　`↘ failed`

### `BackgroundTasks` 的限制

| 限制 | 后果 |
|---|---|
| **跑在同一个进程里** | 进程重启，跑一半的任务就没了 |
| **没有重试 / 超时** | 崩了就崩了 |
| **没有队列** | 不能跨机器 |

**生产上用 Celery / arq / Redis 队列**（以后学）。**现在够用。**

---

## 六、三个标准接口（任何"提交任务"的服务都长这样）

| 方法 | 路径 | 作用 |
|---|---|---|
| **`POST`** | `/tasks` | **提交**，返回 `task_id` + `status: pending` |
| **`GET`** | `/tasks/{task_id}` | **查进度** |
| **`GET`** | `/tasks` | **列出全部** |

**交互模式**：**提交 → 立刻返回 id → 前端轮询状态 → 完成时拿结果。**

---

## 七、`TASKS` 这个"记事本"

```python
TASKS: dict[str, dict] = {}
```

**运行时长这样**：

```python
TASKS = {
    "TASK-c39c447d": {"task_id": "TASK-c39c447d", "name": "tom", "status": "success", ...},
    "TASK-b34a407e": {"task_id": "TASK-b34a407e", "name": "rose", "status": "failed", ...},
}
```

**两层**：外层是"编号 → 任务"，内层是任务的各个字段。

### 改状态的写法是"两层取值"

```python
TASKS["TASK-c39c447d"]                    # → {"name":"tom","status":"pending",...}
TASKS["TASK-c39c447d"]["status"]          # → "pending"
TASKS["TASK-c39c447d"]["status"] = "running"   # → 改成 "running"
```

> **⚠️ 它在内存里 —— 服务一重启就清空。**
> **练习够用。真实项目要存数据库（阶段 B1–B2）。**

---

## 八、`task_id` 怎么生成的

```python
task_id = f"TASK-{uuid.uuid4().hex[:8]}"
```

**一步步拆**：

```python
uuid.uuid4()          # → UUID('c39c447d-8f2a-4b1c-...')   随机唯一标识
       .hex           # → 'c39c447d8f2a4b1c...'            去掉横杠的 32 位
          [:8]        # → 'c39c447d'                       取前 8 位
f"TASK-{...}"         # → 'TASK-c39c447d'                 拼前缀
```

**为什么用随机 id**：**多个用户同时提交，id 不能重复。** 用递增数字在多进程/多机时会撞。

---

## 九、踩的坑

### ⚠️ 1. ⭐ **404 不等于代码写错 —— 可能是端口被别的服务占着**

**今天真实发生的**：

```
ERROR: [Errno 48] error while attempting to bind on address ('127.0.0.1', 8000):
       address already in use
```

**然后所有 curl 都返回 404** —— 因为请求打到了**另一个 app**（`app1.py`，它只有 `/hello`）。

**诊断三步**：

```bash
lsof -i :8000 -P -n                                   # 谁占着
curl -s http://127.0.0.1:8000/openapi.json | python3 -c "
import json,sys; d=json.load(sys.stdin); [print(p) for p in d['paths']]"
                                                       # 这个服务有哪些接口
grep -n "app.get\|app.post" app.py                     # 你的代码有哪些接口
```

**修法**：

```bash
kill $(lsof -ti :8000) 2>/dev/null
sleep 1
lsof -i :8000        # 应该没输出
```

### ⚠️ 2. `@router.get("")` vs `@router.get("/")`

```python
prefix = "/tasks"
@router.get("")     → /tasks       ✅
@router.get("/")    → /tasks/      ← 访问 /tasks 会 404
```

### ⚠️ 3. `bg.add_task` 第一个参数**不能加括号**

```python
bg.add_task(run_task, task_id, req)      # ✅
bg.add_task(run_task(task_id, req))      # ❌ 立刻执行了
```

### ⚠️ 4. 启动命令要写 `app.main:app`

```bash
uvicorn app.main:app --reload
#       └──┬───┘ └┬┘
#      app/main.py 里的 app 变量
```

**不是 `uvicorn main:app`** —— 因为 `main.py` 在 `app/` 里。

**必须从 `day37_router/` 目录启动**（`app` 包的上一级）。

### ⚠️ 5. `BackgroundTasks` 里抛异常没人管

```python
def run_task(...):
    raise ValueError("炸了")     # ← 不会报给客户端，只打到服务器日志
```

**所以一定要在 `run_task` 里 `try/except` 并写进 `TASKS[task_id]["error"]`。**

### ⚠️ 6. `__init__.py` 少了会 import 失败

```
app/__init__.py          ← 必须有（空文件也行）
app/routers/__init__.py  ← 必须有
```

---

## 十、从"脚本"到"服务"

| | Day 27 的 `scheduler.py` | Day 37 的服务 |
|---|---|---|
| 谁用 | **只能你自己** | **任何人 / 任何程序** |
| 何时跑 | 你敲命令时 | **随时** |
| 状态在哪 | 打印完就没了 | **存在 `TASKS` 里** |
| 能不能并发 | 一份 | **多个客户端同时用** |

> **这一步的意义：你写的东西从"练习"变成了"产品"。**

---

## 十一、命令速查

```bash
# 清端口
kill $(lsof -ti :8000) 2>/dev/null; sleep 1; lsof -i :8000

# 启动
cd ~/dev/ai-learning/day37_router
../.venv/bin/python -m uvicorn app.main:app --reload

# 看接口列表
curl -s http://127.0.0.1:8000/openapi.json | python3 -c "
import json,sys; d=json.load(sys.stdin); [print(p) for p in d['paths']]"

# 提交任务
curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"tom","seconds":3}' http://127.0.0.1:8000/tasks

# 查状态
curl http://127.0.0.1:8000/tasks/TASK-xxxxxxxx

# 列出全部
curl http://127.0.0.1:8000/tasks
```

---

## 十二、还没搞懂的

1. `BackgroundTasks` 和真正的任务队列（Celery）差在哪？什么时候必须换？
2. 多个工人（`uvicorn --workers 4`）时，`TASKS` 这个内存字典还准吗？
3. `response_model` 过滤字段的具体规则是什么？
4. `prefix` 能不能嵌套（router 里再挂 router）？
5. 一个公司项目大概几个 router 比较合理？
