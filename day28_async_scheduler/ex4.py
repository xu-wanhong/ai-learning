"""ex4 · 两种限流写法 —— 效果完全一样
"""
import asyncio
import time

DUR = [3, 1, 4, 2, 1, 2, 3, 2]
LIMIT = 3


async def job(i, seconds):
    await asyncio.sleep(seconds)
    return i


async def semaphore_model():
    """写法 1：一次造所有 Task，用 Semaphore 守卫"""
    sem = asyncio.Semaphore(LIMIT)

    async def guarded(i, d):
        async with sem:
            return await job(i, d)

    t0 = time.perf_counter()
    await asyncio.gather(*(guarded(i, d) for i, d in enumerate(DUR)))
    return time.perf_counter() - t0


async def consumer_model():
    """写法 2：只造 LIMIT 个消费者，从队列里取"""
    q = asyncio.Queue()

    async def consumer():
        while True:
            i, d = await q.get()
            await job(i, d)
            q.task_done()

    workers = [asyncio.create_task(consumer()) for _ in range(LIMIT)]

    t0 = time.perf_counter()
    for i, d in enumerate(DUR):
        await q.put((i, d))
    await q.join()
    elapsed = time.perf_counter() - t0

    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)
    return elapsed


async def main():
    print(f"8 个任务 {DUR}，限流 {LIMIT}\n")
    print(f"① 信号量模型 : {await semaphore_model():.2f}s")
    print(f"② 消费者模型 : {await consumer_model():.2f}s")


asyncio.run(main())
