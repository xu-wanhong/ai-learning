"""Day 38 · 题2 —— 找出病态接口并修好

5 个接口，都"要等 0.5 秒"，但写法不同：

    /slow-ok     async def + await asyncio.sleep   ✅ 对照
    /slow-bad    async def + requests.get          ❌ 病态（堵死事件循环）
    /slow-fix1   async def + await httpx           ✅ 修法 1
    /slow-fix2   async def + asyncio.to_thread     ✅ 修法 2
    /slow-fix3   def + requests.get                ✅ 修法 3

启动（先起下游，再起这个）：
    ../.venv/bin/python -m uvicorn downstream:app --port 8078
    ../.venv/bin/python -m uvicorn slow_app:app --port 8077

压测：
    ../.venv/bin/python bench_slow.py
"""
import asyncio
import time

import httpx
import requests
from fastapi import FastAPI

app = FastAPI(title="Day 38 · 题2")

DOWNSTREAM = "http://127.0.0.1:8078/slow-target"


@app.get("/slow-ok")
async def slow_ok():
    """对照：不调外部服务，就是等 0.5 秒"""
    await asyncio.sleep(0.5)
    return {"ok": True}


@app.get("/slow-bad")
async def slow_bad():
    """❌ 病态：async def 里调同步阻塞库"""
    requests.get(DOWNSTREAM, timeout=30)      # ← 没有 await，按死事件循环
    return {"ok": True}


@app.get("/slow-fix1")
async def slow_fix1():
    """✅ 修法 1：换成异步库"""
    async with httpx.AsyncClient(timeout=30) as c:
        await c.get(DOWNSTREAM)
    return {"ok": True}


@app.get("/slow-fix2")
async def slow_fix2():
    """✅ 修法 2：把同步函数丢进线程池"""
    await asyncio.to_thread(requests.get, DOWNSTREAM, timeout=30)
    return {"ok": True}


@app.get("/slow-fix3")
def slow_fix3():
    """✅ 修法 3：接口改成普通 def（代码没变，FastAPI 自动进线程池）"""
    requests.get(DOWNSTREAM, timeout=30)
    return {"ok": True}
