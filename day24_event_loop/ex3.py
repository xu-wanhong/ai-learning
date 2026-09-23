import asyncio
import time


async def work(name, delay):
    await asyncio.sleep(delay)
    return f"{name}({delay}s)"


async def main():
    jobs = [("A", 0.3), ("B", 0.1), ("C", 0.2)]

    # ① gather：结果顺序 = 传入顺序
    t0 = time.perf_counter()
    results = await asyncio.gather(*(work(n, d) for n, d in jobs))
    print("gather 结果：", results)
    print(f"gather 耗时：{time.perf_counter() - t0:.2f}s\n")

    # ② as_completed：结果顺序 = 完成顺序
    t0 = time.perf_counter()
    tasks = [asyncio.create_task(work(n, d)) for n, d in jobs]
    for done in asyncio.as_completed(tasks):
        print("完成：", await done, f"（累计 {time.perf_counter() - t0:.2f}s）")
    print(f"as_completed 耗时：{time.perf_counter() - t0:.2f}s")


asyncio.run(main())