# 【需求】Day 28 核心题：把 Day 27 的调度器改成 asyncio 版
#         8 个任务（其中 2 个失败），用 Semaphore(3) 限制并发数为 3
#         try/except 处理失败 + 状态表 + 汇总
#
# 【验收】总耗时 ≈ 7.0s（和 Day 27 的线程池版一致）
#         成功 6 / 失败 2
#         状态表 8 项


import asyncio
import time


async def ai_task(task_id, name, seconds, boom=False):
    print(f"{task_id} 开始执行")
    await asyncio.sleep(seconds)
    if boom:
        raise ValueError(f"{name} 执行失败")
    print(f"{task_id} 执行结束")
    return f"{name} 执行成功"


MAX_CONCURRENT = 3
TASKS = [
    ("task_001", "tom",  3, False),
    ("task_002", "jack", 1, False),      
    ("task_003", "rose", 4, True),
    ("task_004", "lucy", 2, False),
    ("task_005", "bob",  1, False),
    ("task_006", "amy",  2, True),
    ("task_007", "ken",  3, False),
    ("task_008", "zoe",  2, False),
]


async def main():
    success = 0
    failed = 0
    results = {}
    future_map = {}
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    t0 = time.perf_counter()

    async def limited(ta, na, se, bo):
        async with sem:                              
            return await ai_task(ta, na, se, bo)     

    # ① 点火
    for t, n, s, b in TASKS:
        task = asyncio.create_task(limited(t, n, s, b))
        future_map[task] = (t, n)

    # ② 收货（按完成顺序）
    async for f in asyncio.as_completed(future_map):     # ← async for
        task_id, name = future_map[f]
        try:
            result = await f                             # ← await，不是 .result()
            success += 1
            results[task_id] = {"name": name, "status": "success", "result": result}
            print(f"{task_id} | {name:5} | success")
        except ValueError as e:
            failed += 1
            results[task_id] = {"name": name, "status": "failed", "error": str(e)}
            print(f"{task_id} | {name:5} | failed  | {e}")     # ← 补上 e

    print(f"\n成功 {success} / 失败 {failed}   总耗时 {time.perf_counter() - t0:.2f}s")
    print("状态表：", results)


asyncio.run(main())
