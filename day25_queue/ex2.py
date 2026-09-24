import asyncio
import time


async def producer(q, n):
    for i in range(n):
        await asyncio.sleep(0.2)
        await q.put(f"任务{i}")
        print(f"  生产：任务{i}")


async def consumer(q,name,n):
    for _ in range(n):
        item=await q.get()
        await asyncio.sleep(0.5)
        print(f"{name} 处理完：{item}")


async def main():
    t0=time.perf_counter()
    q=asyncio.Queue()
    await asyncio.gather(
        producer(q,5),
        consumer(q,"消费者",5),
    )
    print(f"总耗时：{time.perf_counter() - t0:.2f}s")


asyncio.run(main())