import asyncio
import time

import httpx

BASE = "http://127.0.0.1:8765"


async def fetch_wrong(i):
    r = httpx.get(f"{BASE}/page{i}", timeout=10)     # ← 同步调用，按住事件循环
    return f"page{i} → {r.status_code}"


async def main():
    t0 = time.perf_counter()
    results = await asyncio.gather(*(fetch_wrong(i) for i in range(10)))
    for line in results:
        print(line)
    print(f"异步外壳 + 同步 httpx.get：{time.perf_counter() - t0:.2f}s")


asyncio.run(main())