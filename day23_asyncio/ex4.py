import asyncio
import time

async def good (name,delay):
    await asyncio.sleep(delay)
    return name

async def bad (name,delay):
    time.sleep(delay)
    return name

async def main ():
    start =time.perf_counter()
    await asyncio.gather(
        good("q",1),
        good("b",1),
        good("t",1)
    )
    print(f"总耗时：{time.perf_counter()-start:.2f}s")

    start=time.perf_counter()
    await asyncio.gather(
        bad("q",1),
        bad("b",1),
        bad("t",1)
    )
    print(f"总耗时:{time.perf_counter()-start:.2f}s")

asyncio.run(main())