"""ex2 · 不限流 vs Semaphore(3)
"""
import asyncio
import time

DUR = [3, 1, 4, 2, 1, 2, 3, 2]              # 8 个任务的耗时


async def job(i, seconds):
    await asyncio.sleep(seconds)
    return i


async def run(limit=None):
    """limit=None → 不限流；limit=3 → 最多 3 个同时跑"""
    t0 = time.perf_counter()

    if limit is None:
        await asyncio.gather(*(job(i, d) for i, d in enumerate(DUR)))

    else:
        sem = asyncio.Semaphore(limit)

        async def guarded(i, d):
            async with sem:                  
                return await job(i, d)      

        await asyncio.gather(*(guarded(i, d) for i, d in enumerate(DUR)))

    return time.perf_counter() - t0          


async def main():
    print(f"8 个任务 {DUR}")
    print(f"串行总和 = {sum(DUR)}s，最长任务 = {max(DUR)}s\n")

    unlimited = await run()
    limited = await run(3)

    print(f"不限流       : {unlimited:.2f}s")
    print(f"Semaphore(3) : {limited:.2f}s")


asyncio.run(main())
