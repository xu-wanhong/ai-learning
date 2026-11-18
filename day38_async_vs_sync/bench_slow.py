"""Day 38 · 题2 压测：10 个并发，看 5 个接口各要多久

预期：
    /slow-ok     →  ≈0.5s
    /slow-bad    →  ≈5.0s   ← 10 个排队（最糟）
    /slow-fix1   →  ≈0.5s
    /slow-fix2   →  ≈0.5s
    /slow-fix3   →  ≈0.5s
"""
import asyncio
import time

import httpx

BASE = "http://127.0.0.1:8077"
N = 10


async def main():
    async with httpx.AsyncClient(timeout=120) as c:
        for name in ("slow-ok", "slow-bad", "slow-fix1", "slow-fix2", "slow-fix3"):
            t0 = time.perf_counter()
            rs = await asyncio.gather(*(c.get(f"{BASE}/{name}") for _ in range(N)))
            codes = {r.status_code for r in rs}
            print(f"  /{name:10} → {time.perf_counter() - t0:5.2f}s   状态码 {codes}")


if __name__ == "__main__":
    asyncio.run(main())
