import asyncio
import time

N = 10
DELAY = 0.2


async def io_async(i):
    await asyncio.sleep(DELAY)
    return i


async def io_blocking(i):
    time.sleep(DELAY)      # 故意用错
    return i


async def run_serial(n):
    """串行：一个 await 完再下一个"""
    t0 = time.perf_counter()
    for i in range(n):
        await io_async(i)
    return time.perf_counter() - t0


async def run_gather(n):
    """并发：正确的 asyncio.sleep"""
    t0 = time.perf_counter()
    await asyncio.gather(*(io_async(i) for i in range(n)))
    return time.perf_counter() - t0


async def run_wrong(n):
    """并发外壳 + 阻塞的 time.sleep"""
    t0 = time.perf_counter()
    await asyncio.gather(*(io_blocking(i) for i in range(n)))
    return time.perf_counter() - t0


async def main():
    serial = await run_serial(N)
    gathered = await run_gather(N)
    wrong = await run_wrong(N)
    print(f"N = {N}，每个任务 {DELAY}s，理论最优 {DELAY}s\n")
    print(f"串行 await         : {serial:.2f}s")
    print(f"asyncio.gather     : {gathered:.2f}s   加速比 {serial / gathered:.2f}x")
    print(f"gather + time.sleep: {wrong:.2f}s   加速比 {serial / wrong:.2f}x")


asyncio.run(main())