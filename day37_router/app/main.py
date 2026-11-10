"""Day 37 · 入口：创建 app，把路由挂上去"""
from fastapi import FastAPI

from app.routers import tasks

app = FastAPI(title="Day 37 · 任务调度服务")

app.include_router(tasks.router)


@app.get("/health", tags=["系统"])
def health():
    return {"status": "ok"}
