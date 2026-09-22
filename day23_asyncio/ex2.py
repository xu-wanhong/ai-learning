import asyncio
import time 

async def job (name,delay):
    print(f"{name}：开始")
    await asyncio.sleep(1.5)
    print(f"{name}:结束")
    return name

async def main ():
    start = time.perf_counter()
    await job("q",1)
    await job("b",1)
    await job("t",1)
    print(f"总用时；{time.perf_counter()-start:.2f}s")

asyncio.run(main())



