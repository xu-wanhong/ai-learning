"""Day 38 · 压测：同时发 10 个请求，看总耗时

用法（先另开一个终端起服务）：
    cd ~/dev/ai-learning/day38_async_vs_sync
    ../.venv/bin/python -m uvicorn app:app --port 8000

    # 然后：
    ../.venv/bin/python bench.py

预期（N=10，每个等 0.5 秒）：
    /a-async-sleep  →  ≈ 0.5s
    /b-async-block  →  ≈ 5.0s   ← 10 个排队
    /c-sync         →  ≈ 0.5s
"""
import asyncio
import time

import httpx

BASE = "http://127.0.0.1:8000"
N = 10


async def bench(client: httpx.AsyncClient, path: str) -> float:
    """同时发 N 个请求，返回总耗时"""
    t0 = time.perf_counter()
    await asyncio.gather(*(client.get(f"{BASE}{path}") for _ in range(N)))
    return time.perf_counter() - t0


async def main():
    print(f"{N} 个并发请求，每个接口内部要等 0.5 秒\n")
    cases = [
        ("✅ async def + await asyncio.sleep", "/a-async-sleep"),
        ("❌ async def + time.sleep（阻塞）", "/b-async-block"),
        ("🟡 def + time.sleep（线程池）", "/c-sync"),
    ]
    async with httpx.AsyncClient(timeout=60) as client:
        for label, path in cases:
            t = await bench(client, path)
            print(f"  {label:38} → {t:5.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
