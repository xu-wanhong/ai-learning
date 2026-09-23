import asyncio
import time

async def work (name,delay):
    print(f"{name}:开始")
    await asyncio.sleep(delay)
    print(f"{name}:结束")
    return name

async def main ():
    t0=time.perf_counter()
    print("--- 创建两个任务 ---")
    
    t1=asyncio.create_task(work("q",1))
    t2=asyncio.create_task(work("b",1))
    
    print("--- 任务已创建，还没 await ---")

    await t1
    await t2

    print(f"总耗时：{time.perf_counter()-t0:.2f}s")


asyncio.run(main())