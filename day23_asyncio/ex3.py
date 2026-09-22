import asyncio
import time

async def job (name,delay):
    print(f"{name}：开始") 
    await asyncio.sleep(delay)
    print(f"{name}：结束")
    return name

async def main ():
    start=time.perf_counter()
    result=await asyncio.gather ( 
        job("q",1),
        job("b",1),
        job("t",1)
    )
    print(f"结果：{result}")
    print(f"总用时：{time.perf_counter()-start:.2f}s")

asyncio.run(main())