"""模拟"外部慢 API"（比如 LLM 服务）—— 必须单独起一个进程

为什么不能在自己身上调自己？
    因为 /slow-bad 里的 requests.get 会按住事件循环，
    被调的接口也在同一个循环上 → 永远轮不到它响应 → 死锁 → 10 秒超时。

启动：
    ../.venv/bin/python -m uvicorn downstream:app --port 8078
"""
import time

from fastapi import FastAPI

app = FastAPI()


@app.get("/slow-target")
def slow_target():
    time.sleep(0.5)
    return {"ok": True}
