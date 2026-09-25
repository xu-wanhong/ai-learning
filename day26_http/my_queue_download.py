import asyncio
import time

import httpx

BASE = "http://127.0.0.1:8765"
N = 9           # 任务数
WORKERS = 3     # 消费者数


async def producer(q, n):
    for i in range(n):
        await q.put(f"{BASE}/page{i}")
        print(f"生产：page{i}")


async def consumer(q, client, name, done):
    while True:
        url = await q.get()                        
        r = await client.get(url, timeout=10)      
        done.append((url, r.status_code))
        print(f"{name} 完成 {url} → {r.status_code}")
        q.task_done()                              

async def main():
    q = asyncio.Queue()
    done = []
    t0 = time.perf_counter()

    async with httpx.AsyncClient(timeout=10) as client:      
        workers = [
            asyncio.create_task(consumer(q, client, f"消费者{i}", done))
            for i in range(WORKERS)
        ]

        await producer(q, N)
        await q.join()

        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

    ok = sum(1 for _, code in done if code == 200)
    print(f"\n成功 {ok}/{N} 个，耗时 {time.perf_counter() - t0:.2f}s")


asyncio.run(main())
