import asyncio


async def safe_worker(q, box):
    while True:
        await q.get()
        box["n"] = box["n"] + 1     # 读-改-写，中间没有 await
        q.task_done()


async def risky_worker(q, box):
    while True:
        await q.get()
        tmp = box["n"]              # 读
        await asyncio.sleep(0)      # ← 让位点！别人能在这中间插进来
        box["n"] = tmp + 1          # 写
        q.task_done()


async def run(worker, n_workers, n_jobs):
    q = asyncio.Queue()
    box = {"n": 0}
    workers = [asyncio.create_task(worker(q, box)) for _ in range(n_workers)]
    for i in range(n_jobs):
        await q.put(i)
    await q.join()
    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)
    return box["n"]


async def main():
    print("期望值：100\n")
    print("安全版（读-改-写 中间没有 await）:", await run(safe_worker, 3, 100))
    print("危险版（中间插了 sleep(0)）     :", await run(risky_worker, 3, 100))


asyncio.run(main())