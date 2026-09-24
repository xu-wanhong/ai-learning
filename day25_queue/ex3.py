import asyncio
import time


async def producer(q, n):
    for i in range(n):
        await q.put(f"任务{i}")
        print(f"  生产：任务{i}")
        await asyncio.sleep(0.1)


async def consumer(q, name):
    while True:
        item = await q.get()
        await asyncio.sleep(0.3)
        print(f"{name} 完成 {item}")
        q.task_done()          


async def main():
    q = asyncio.Queue()
    t0 = time.perf_counter()

    workers = [asyncio.create_task(consumer(q, f"消费者{i}")) for i in range(3)]

    await producer(q, 9)
    await q.join()             
    print(f"--- 9 个任务全部处理完，耗时 {time.perf_counter() - t0:.2f}s ---")

    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)


asyncio.run(main())