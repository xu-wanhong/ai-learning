import asyncio

async def main ():
    q=asyncio.Queue()
    await q.put("b")
    await q.put("t")

    print("放进去两个，qsize=",q.qsize())

    print("取出" ,await q.get())
    print("取出" ,await q.get())

    print("qsize =", q.qsize(), " empty =", q.empty())


asyncio.run(main())