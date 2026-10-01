"""ex1 · asyncio 版调度器（最小版）
"""
import asyncio
import time

TASKS = [
    ("TASK-001", "Tom",  3),
    ("TASK-002", "Jack", 1),
    ("TASK-003", "Rose", 4),
    ("TASK-004", "Lucy", 2),
]


async def ai_task(task_id, name, seconds):
    print(f"{task_id} 开始执行")
    await asyncio.sleep(seconds)                  
    print(f"{task_id} 执行结束")
    return f"{name} 执行成功"


async def main():
    future_map = {}
    t0 = time.perf_counter()

    
    for tid, name, seconds in TASKS:
        task = asyncio.create_task(ai_task(tid, name, seconds))
        future_map[task] = (tid, name)

    
    async for f in asyncio.as_completed(future_map):    # ← async for！
        task_id, name = future_map[f]
        result = await f                                # ← await，不是 .result()
        print(f"{task_id} | {name:5} | {result}")

    print(f"\n总耗时：{time.perf_counter() - t0:.2f}s")


asyncio.run(main())
