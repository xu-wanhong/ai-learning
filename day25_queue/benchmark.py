import asyncio
import time

N_JOBS = 9
JOB_TIME = 0.3


async def consumer(q, done):
    while True:
        item = await q.get()
        await asyncio.sleep(JOB_TIME)
        done.append(item)
        q.task_done()


async def run_with(n_consumers):
    q = asyncio.Queue()
    done = []
    for i in range(N_JOBS):
        await q.put(i)

    t0 = time.perf_counter()
    workers = [asyncio.create_task(consumer(q, done)) for _ in range(n_consumers)]
    await q.join()
    elapsed = time.perf_counter() - t0

    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)

    return elapsed, len(done)


async def main():
    base = None
    print(f"{N_JOBS} 个任务，每个 {JOB_TIME}s，理论最优 {JOB_TIME}s\n")
    for n in (1, 3, 9):
        elapsed, count = await run_with(n)
        if base is None:
            base = elapsed
        print(f"消费者数 = {n} : {elapsed:.2f}s   加速比 {base / elapsed:.2f}x   已处理 {count}")


asyncio.run(main())
    