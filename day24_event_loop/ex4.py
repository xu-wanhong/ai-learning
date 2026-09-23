"""用生成器模拟：事件循环到底在干什么"""

from collections import deque


def task_a():
    print("  A 第一步")
    yield "让位"          # ← 相当于 await
    print("  A 第二步")
    yield "让位"
    print("  A 第三步")


def task_b():
    print("  B 第一步")
    yield "让位"
    print("  B 第二步")


def run(*tasks):
    queue = deque(tasks)
    step = 0
    while queue:
        step += 1
        task = queue.popleft()
        try:
            print(f"[第 {step} 圈] 轮到 {task.__name__}")
            next(task)
            queue.append(task)          # 没跑完，放回队尾
        except StopIteration:
            print(f"[第 {step} 圈] {task.__name__} 结束")


print("=== 手写的最小事件循环 ===")
run(task_a(), task_b())