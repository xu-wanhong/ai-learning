import asyncio
import time

import httpx

BASE = "http://127.0.0.1:8765"


async def fetch(client, i):
    r = await client.get(f"{BASE}/page{i}")
    return f"page{i} → {r.status_code}"


async def main():
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=10) as client:
        results = await asyncio.gather(*(fetch(client, i) for i in range(10)))
    for line in results:
        print(line)
    print(f"异步并发 10 个请求：{time.perf_counter() - t0:.2f}s")


asyncio.run(main())


    
