"""ex3 · 峰值并发测量 —— 限流的【直接证据】
"""
import asyncio
import time

DUR = [3, 1, 4, 2, 1, 2, 3, 2]

running = 0            # 此刻有几个在跑
peak = 0               # 历史最高


async def job(i, seconds):
    global running, peak
    running += 1
    peak = max(peak, running)
    await asyncio.sleep(seconds)
    running -= 1
    return i


async def run_unlimited(durations):
    """① 不限流：一次把所有的都放出去"""
    global running, peak
    running = 0                            # ⚠️ 测量前必须清零
    peak = 0
    t0 = time.perf_counter()
    await asyncio.gather(*(job(i, d) for i, d in enumerate(durations)))
    return time.perf_counter() - t0, peak


async def run_limited(durations, limit):
    """② 限流：最多 limit 个同时跑"""
    global running, peak
    running = 0
    peak = 0
    sem = asyncio.Semaphore(limit)

    async def guarded(i, d):
        async with sem:
            return await job(i, d)

    t0 = time.perf_counter()
    await asyncio.gather(*(guarded(i, d) for i, d in enumerate(durations)))
    return time.perf_counter() - t0, peak


async def main():
    print(f"8 个任务，耗时 {DUR}")
    print(f"串行总和 = {sum(DUR)}s，最长任务 = {max(DUR)}s\n")

    t, p = await run_unlimited(DUR)
    print(f"① 不限流       : {t:.2f}s   峰值并发 = {p}")

    t, p = await run_limited(DUR, 3)
    print(f"② Semaphore(3) : {t:.2f}s   峰值并发 = {p}")


asyncio.run(main())
