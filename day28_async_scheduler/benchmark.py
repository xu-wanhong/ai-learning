"""benchmark · 四组终极对比（Day 28 的全部结论）

    并发度 = 3 ─┬─ asyncio + Semaphore(3) : 7.00s
                └─ 线程池(3)              : 7.01s

    并发度 = 8 ─┬─ asyncio 不限流         : 4.00s
                └─ 线程池(8)              : 4.01s

【结论】两种完全不同的机制（协程 vs 线程），只要并发度一样，耗时几乎完全一样。
        Semaphore(3) 和 max_workers=3 是同一件事的两种表达。

参照数字：
    sum(DUR) = 18s   ← 串行耗时
    max(DUR) = 4s    ← 并发度 ≥ 任务数时的耗时
"""
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

DUR = [3, 1, 4, 2, 1, 2, 3, 2]


# ---------------- asyncio ----------------
async def a_job(i, d):
    await asyncio.sleep(d)
    return i


async def a_unlimited():
    t0 = time.perf_counter()
    await asyncio.gather(*(a_job(i, d) for i, d in enumerate(DUR)))
    return time.perf_counter() - t0


async def a_limited(limit):
    sem = asyncio.Semaphore(limit)

    async def guarded(i, d):
        async with sem:
            return await a_job(i, d)

    t0 = time.perf_counter()
    await asyncio.gather(*(guarded(i, d) for i, d in enumerate(DUR)))
    return time.perf_counter() - t0


# ---------------- 线程池 ----------------
def b_job(d):
    time.sleep(d)


def b_pool(workers):
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(b_job, DUR))
    return time.perf_counter() - t0


async def main():
    print(f"8 个任务 {DUR}")
    print(f"串行总和 = {sum(DUR)}s，最长任务 = {max(DUR)}s\n")

    au = await a_unlimited()
    al = await a_limited(3)
    print(f"asyncio 不限流       : {au:.2f}s   （并发度 8）")
    print(f"asyncio Semaphore(3) : {al:.2f}s   （并发度 3）")

    print()
    b3 = b_pool(3)
    b8 = b_pool(8)
    print(f"线程池(3)            : {b3:.2f}s   （并发度 3）")
    print(f"线程池(8)            : {b8:.2f}s   （并发度 8）")


asyncio.run(main())
