"""Day 38 · async def vs def —— 三种组合的性能对比

三种接口，内部都是"等 0.5 秒"，但写法不同：

    /a-async-sleep   async def + await asyncio.sleep   ✅ 最好
    /b-async-block   async def + time.sleep            ❌ 最糟（堵死事件循环）
    /c-sync          def + time.sleep                  🟡 能接受（线程池兜底）

启动：
    cd ~/dev/ai-learning/day38_async_vs_sync
    ../.venv/bin/python -m uvicorn app:app --port 8000

压测：
    ../.venv/bin/python bench.py
"""
import asyncio
import time

from fastapi import FastAPI

app = FastAPI(title="Day 38 · async vs sync")

SLEEP = 0.5


@app.get("/health", tags=["系统"])
def health():
    return {"status": "ok"}


# ---------- ✅ 最好：async def + await ----------
@app.get("/a-async-sleep", tags=["对比"])
async def a_async_sleep():
    """await 会让出控制权 —— 等的时候事件循环去处理别的请求"""
    await asyncio.sleep(SLEEP)
    return {"ok": True, "方式": "async def + await asyncio.sleep"}


# ---------- ❌ 最糟：async def + 同步阻塞 ----------
@app.get("/b-async-block", tags=["对比"])
async def b_async_block():
    """time.sleep 不会让出控制权 —— 把这 0.5 秒里整个事件循环按住"""
    time.sleep(SLEEP)
    return {"ok": True, "方式": "async def + time.sleep（错误示范）"}


# ---------- 🟡 能接受：def + 同步阻塞 ----------
@app.get("/c-sync", tags=["对比"])
def c_sync():
    """普通 def —— FastAPI 会自动丢进线程池，不会堵住事件循环"""
    time.sleep(SLEEP)
    return {"ok": True, "方式": "def + time.sleep（线程池兜底）"}
