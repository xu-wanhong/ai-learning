"""ex4 · to_thread —— 在 asyncio 里调用【只有同步版】的老库

【问题】
asyncio 里直接调同步阻塞函数（老库的 requests.get、time.sleep、文件读写），
会把【整个事件循环按住】—— 别的协程全得干等。
你以为在并发，其实退化成了串行，而且看不出来。

【解法】
    await asyncio.to_thread(阻塞函数, 参数...)
它把那个函数丢进【线程池】跑，事件循环立刻腾出来去干别的。

【什么时候用】
调用只有同步版本的老库：requests / 老 SDK / 图像处理 / 大文件读写

【老写法（3.9 之前）】
    await loop.run_in_executor(None, func, *args)
    （能指定进程池：run_in_executor(process_pool, 重计算函数)）

【怎么看出事件循环被按住了】
    用「心跳」协程：每 0.1s 打一个 ♥，带时间戳。

    ❌ 直接调同步函数   → ♥0.1 ♥0.2 【然后沉默整整 1 秒】
    ✅ to_thread 包起来 → ♥0.1 ♥0.2 ♥0.3 ♥0.4 ♥0.5 【一直在跳】
"""
import asyncio
import time

T0 = 0.0


async def heartbeat(seconds):
    """每 0.1 秒打一个 ♥（带时间戳）—— 用来证明事件循环还活着"""
    global T0
    while time.perf_counter() - T0 < seconds:
        await asyncio.sleep(0.1)
        print(f"♥{time.perf_counter() - T0:.1f} ", end="", flush=True)


def blocking_io(name, seconds):
    """同步阻塞函数（假装是个老库）"""
    time.sleep(seconds)                          # ← 注意：time.sleep，不是 await
    return f"{name} 完成"


async def bad():
    """❌ 直接调同步函数 —— 事件循环被按住"""
    global T0
    print("  ❌ 直接调同步函数：")
    T0 = time.perf_counter()
    hb = asyncio.create_task(heartbeat(3.0))
    await asyncio.sleep(0.25)                    # 先让心跳跳两下，证明循环本来是活的
    print("\n     ", end="", flush=True)

    t0 = time.perf_counter()
    blocking_io("BAD-1", 0.5)                    # ← 这 1 秒里事件循环【死住】
    blocking_io("BAD-2", 0.5)
    blocked = time.perf_counter() - t0

    print(f"\n      ↑ 两个阻塞函数共 {blocked:.2f}s —— 这期间心跳【一个都没打】")
    hb.cancel()
    await asyncio.gather(hb, return_exceptions=True)


async def good():
    """✅ to_thread 丢进线程池 —— 真并发"""
    global T0
    print("  ✅ to_thread（丢进线程池）：")
    T0 = time.perf_counter()
    hb = asyncio.create_task(heartbeat(3.0))
    await asyncio.sleep(0.25)
    print("\n     ", end="", flush=True)

    t0 = time.perf_counter()
    await asyncio.gather(
        asyncio.to_thread(blocking_io, "GOOD-1", 0.5),
        asyncio.to_thread(blocking_io, "GOOD-2", 0.5),
    )
    elapsed = time.perf_counter() - t0

    print(f"\n      ↑ 两个 0.5s 共 {elapsed:.2f}s（真并发）—— 心跳【一直在跳】")
    hb.cancel()
    await asyncio.gather(hb, return_exceptions=True)


async def main():
    await bad()
    print()
    await good()


asyncio.run(main())
