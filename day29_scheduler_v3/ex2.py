"""ex2 · 超时的三个行为

① wait_for 超时        → 抛 TimeoutError
② 超时后原任务的状态    → 被【取消】了（不是"继续在后台跑"）
③ shield 保护          → 外层超时，内层照样跑完

【为什么这个最重要】
「超时 = 取消」这个事实，是 V3 里所有设计的根基：
    超时的任务要当成【失败】处理（可以重试、可以记 failed），
    而不是"不管它，让它自己在后台跑完"。

【看输出的诀窍】
    超时的那些任务，只有「开始」没有「结束」——
    那就是"被从 await 中间掐掉了"的直接证据。
"""
import asyncio
import time


async def slow(seconds, label="任务"):
    print(f"    {label} 开始（要睡 {seconds}s）")
    await asyncio.sleep(seconds)
    print(f"    {label} 结束")          # ← 被超时掐掉的任务，这行永远不打印
    return f"{label} 完成"


async def main():
    # ---------- ① wait_for 超时 ----------
    print("① wait_for 超时：")
    t0 = time.perf_counter()
    try:
        await asyncio.wait_for(slow(5, "A"), timeout=0.3)
    except TimeoutError:
        print(f"    → TimeoutError，实际耗时 {time.perf_counter() - t0:.2f}s")

    # ---------- ② 超时之后，那个任务还在跑吗？ ----------
    print()
    print("② 超时之后，那个任务还在跑吗？")
    task = asyncio.create_task(slow(5, "B"))
    try:
        await asyncio.wait_for(task, timeout=0.3)
    except TimeoutError:
        pass
    await asyncio.sleep(0)                       # 让事件循环转一圈，使取消生效
    print(f"    task.cancelled() = {task.cancelled()}")
    print(f"    task.done()      = {task.done()}")
    try:
        await task
    except asyncio.CancelledError:
        print("    await task → CancelledError（被取消了，不是「还在跑」）")

    # ---------- ③ shield 保护 ----------
    print()
    print("③ shield 保护：外层超时，内层继续跑")
    task2 = asyncio.create_task(slow(0.6, "C"))
    t0 = time.perf_counter()
    try:
        await asyncio.wait_for(asyncio.shield(task2), timeout=0.2)
    except TimeoutError:
        print(f"    → 外层在 {time.perf_counter() - t0:.2f}s 就超时了")
    print(f"    但内层还在跑 → 最终结果：{await task2}")


asyncio.run(main())
