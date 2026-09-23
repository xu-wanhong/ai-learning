import asyncio
import time

N = 10
DELAY = 0.2


async def work(i):
    await asyncio.sleep(DELAY)
    return i


async def run_all_first(n):
    """先把 n 个任务全部点火，最后统一等"""
    t0 = time.perf_counter()
    tasks = [asyncio.create_task(work(i)) for i in range(n)]
    for t in tasks:
        await t
    return time.perf_counter() - t0


async def run_one_by_one(n):
    """ 每创建一个就立刻 await —— 等于没并发"""
    t0 = time.perf_counter()
    for i in range(n):
        t = asyncio.create_task(work(i))
        await t
    return time.perf_counter() - t0


async def run_gather(n):
    """基准"""
    t0 = time.perf_counter()
    await asyncio.gather(*(work(i) for i in range(n)))
    return time.perf_counter() - t0


async def main():
    a = await run_all_first(N)
    b = await run_one_by_one(N)
    c = await run_gather(N)
    print(f"N = {N}，每个任务 {DELAY}s，理论最优 {DELAY}s\n")
    print(f"先全建再统一 await : {a:.2f}s   加速比 {b / a:.2f}x")
    print(f"边建边 await（错）  : {b:.2f}s   加速比 1.00x")
    print(f"asyncio.gather     : {c:.2f}s   加速比 {b / c:.2f}x")


asyncio.run(main())