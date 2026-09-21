"""Day 22 · 学方法 —— 例 1：最简单的线程池

跑法：
    cd ~/dev/ai-learning/day22_concurrency
    source ../.venv/bin/activate
    python learn_api.py
"""
from concurrent.futures import ThreadPoolExecutor


def work(n):
    return n * 2


with ThreadPoolExecutor(max_workers=1) as ex:
    results = list(ex.map(work, [1, 2, 3]))

print(results)
