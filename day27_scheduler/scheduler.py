from concurrent.futures import ThreadPoolExecutor, as_completed
import time


def ai_task(task_id, name, seconds, boom=False):
    print(f"{task_id} 开始执行")
    time.sleep(seconds)
    if boom:
        raise ValueError(f"{name} 执行失败")
    print(f"{task_id} 执行结束")
    return f"{name} 执行成功"


TASKS = [
    ("TASK-001", "Tom",  3, False),
    ("TASK-002", "Jack", 1, False),
    ("TASK-003", "Rose", 4, True),
    ("TASK-004", "Lucy", 2, False),
    ("TASK-005", "Bob",  1, False),
    ("TASK-006", "Amy",  2, True),
    ("TASK-007", "Ken",  3, False),
    ("TASK-008", "Zoe",  2, False),
]

results = {}
success = 0
failed = 0
t0 = time.perf_counter()

with ThreadPoolExecutor(max_workers=3) as ex:
    future_map = {}
    for tid, name, seconds, boom in TASKS:
        future_map[ex.submit(ai_task, tid, name, seconds, boom)] = (tid, name)

    for f in as_completed(future_map):
        task_id, name = future_map[f]
        try:
            result = f.result()
            success += 1
            results[task_id] = {"name": name, "status": "success", "result": result}
            print(f"{task_id} | {name:5} | success")
        except ValueError as e:
            failed += 1
            results[task_id] = {"name": name, "status": "failed", "error": str(e)}
            print(f"{task_id} | {name:5} | failed  | {e}")

print(f"\n成功 {success} / 失败 {failed}   总耗时 {time.perf_counter()-t0:.2f}s")
print("状态表：", results)
