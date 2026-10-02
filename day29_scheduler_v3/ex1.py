# 需求】写一个睡 5 秒的协程，用两种方式各加一次 0.5 秒的超时，捕获 TimeoutError：
#         ① asyncio.wait_for
#         ② async with asyncio.timeout

# 【验收】两次都在 ≈0.5s 时抛 TimeoutError

import asyncio
import time

async def slow():
    print(" 开始执行")
    await asyncio.sleep(5)
    print("结束执行")
    return "结束"


async def main():
    print("wait_for")
    t0=time.perf_counter()
    try:
        result=await asyncio.wait_for(slow(),timeout=0.5)
        print(f"成功   {result} ")
    except TimeoutError:
        print(f"Timeout  总耗时{time.perf_counter()-t0:.2f}s")

    print("-----asyncio.timeout-----")
    t0=time.perf_counter()
    try:
        async with asyncio.timeout(0.5):
            result=await slow()
            print(f"成功  {result}")
    except TimeoutError:
        print(f"Timeout  总耗时{time.perf_counter()-t0:.2f}s")


asyncio.run(main())



