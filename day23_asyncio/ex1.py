import asyncio


async def hello(name):
    print(f"hello:{name}")
    await asyncio.sleep(1)
    print(f"bye:{name}")

print("直接调用hell0（）")
result=hello("q")
print("拿到的结果:",asyncio.run(result))

print("用asyncio.run,执行")
asyncio.run(hello("q"))

