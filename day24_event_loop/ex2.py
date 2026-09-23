import asyncio
import time

async def work (name,delay):
    print(f"{name}:开始")
    await asyncio.sleep(delay)
    print(f"{name}:结束")
    return f"{name}的结果"

async def main ():
    t = asyncio.create_task(work("q", 1))
    print("刚创建时 done() =", t.done())

    await asyncio.sleep(0)
    print("让出一圈后 done() =", t.done())

    await asyncio.sleep(0.5)
    print("过了 0.5 秒 done() =", t.done())

    result=await t
    print("await 之后 done() =", t.done())
    print("t.result() =", t.result())
    print("拿到的 result =", result)


asyncio.run(main())


