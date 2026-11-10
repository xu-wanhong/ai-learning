"""Day 37 · 任务相关的 3 个接口"""
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models import TaskRequest, TaskInfo

# 一个"分机"：prefix 让所有路径自动加 /tasks，tags 让 /docs 里分组
router = APIRouter(prefix="/tasks", tags=["任务"])

# 内存里的"记事本"：编号 -> 任务信息（服务重启就清空）
TASKS: dict[str, dict] = {}


def run_task(task_id: str, req: TaskRequest):
    """真正干活的地方（在后台跑，不挡用户）"""
    TASKS[task_id]["status"] = "running"
    time.sleep(req.seconds)                      # 真项目这里是调 LLM / 处理文件

    if req.boom:
        TASKS[task_id]["status"] = "failed"
        TASKS[task_id]["error"] = f"{req.name} 执行失败"
    else:
        TASKS[task_id]["status"] = "success"
        TASKS[task_id]["result"] = f"{req.name} 执行成功（耗时 {req.seconds}s）"


@router.post("", response_model=TaskInfo, summary="提交任务")
def create_task(req: TaskRequest, bg: BackgroundTasks):
    # ① 生成随机编号：TASK-xxxxxxxx
    task_id = f"TASK-{uuid.uuid4().hex[:8]}"

    # ② 先登记（状态 pending），这样用户马上就能查到
    TASKS[task_id] = {
        "task_id": task_id,
        "name": req.name,
        "status": "pending",
        "seconds": req.seconds,
        "result": None,
        "error": None,
    }

    # ③ 挂到"待跑"队列：响应发出去之后才执行
    bg.add_task(run_task, task_id, req)

    # ④ 立刻返回
    return TASKS[task_id]


@router.get("", response_model=list[TaskInfo], summary="列出所有任务")
def list_tasks():
    return list(TASKS.values())


@router.get("/{task_id}", response_model=TaskInfo, summary="查单个任务")
def get_task(task_id: str):
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return TASKS[task_id]
