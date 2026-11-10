"""Day 37 · 数据模型（只描述"长什么样"，不写逻辑）"""
from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    """提交任务时，你要发什么"""
    name: str = Field(description="任务名")
    seconds: float = Field(default=1.0, ge=0.1, le=30, description="模拟耗时（秒）")
    boom: bool = Field(default=False, description="是否故意失败")


class TaskInfo(BaseModel):
    """查任务时，你会收到什么"""
    task_id: str
    name: str
    status: str
    seconds: float
    result: str | None = None
    error: str | None = None
