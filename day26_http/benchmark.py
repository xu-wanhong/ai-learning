import asyncio
import time

import httpx

BASE = "http://127.0.0.1:8765"
N = 10


def run_sync():
    t0 = time.perf_counter()
    with httpx.Client(timeout=10) as client:
        for i in range(N):
            client.get(f"{BASE}/page{i}")
    return time.perf_counter() - t0


async def fetch_async(client, i):
    await client.get(f"{BASE}/page{i}")


async def run_async():
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=10) as client:
        await asyncio.gather(*(fetch_async(client, i) for i in range(N)))
    return time.perf_counter() - t0


async def fetch_blocking(i):
    httpx.get(f"{BASE}/page{i}", timeout=10)


async def run_async_but_blocking():
    t0 = time.perf_counter()
    await asyncio.gather(*(fetch_blocking(i) for i in range(N)))
    return time.perf_counter() - t0


async def main():
    httpx.get(f"{BASE}/warmup", timeout=10)          # 热身

    sync = run_sync()
    asy = await run_async()
    bad = await run_async_but_blocking()

    print(f"N = {N} 个请求，服务器每个睡 1s，理论最优 1.0s\n")
    print(f"同步串行 httpx.Client      : {sync:.2f}s   加速比 1.00x")
    print(f"异步并发 AsyncClient       : {asy:.2f}s   加速比 {sync / asy:.2f}x")
    print(f"异步外壳 + 同步 httpx.get  : {bad:.2f}s   加速比 {sync / bad:.2f}x")


asyncio.run(main())