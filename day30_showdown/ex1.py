"""Day 30 把四种跑法封装成函数
"""
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

N = 8
WAIT = 0.3
WORKERS = 8


# ---------------- 任务定义（模块级！）----------------
def wait_task(i):
    """等待型任务 —— 给线程池 / 进程池用"""
    time.sleep(WAIT)
    return i


async def async_wait_task(i):
    """等待型任务 —— 给 asyncio 用"""
    await asyncio.sleep(WAIT)
    return i


# ---------------- 四种跑法（都返回耗时秒数）----------------
def run_serial(fn, n):
    """串行：一个一个来（基准）"""
    t0 = time.perf_counter()
    for i in range(n):
        fn(i)
    return time.perf_counter() - t0


def run_thread(fn, n, workers=WORKERS):
    """线程池"""
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(fn, range(n)))          # ⚠️ 必须消费掉迭代器
    return time.perf_counter() - t0


def run_process(fn, n, workers=WORKERS):
    """进程池"""
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        list(ex.map(fn, range(n)))
    return time.perf_counter() - t0


def run_async(coro_fn, n):
    """asyncio：一次把 n 个协程全放出去"""
    async def _run():
        await asyncio.gather(*(coro_fn(i) for i in range(n)))

    t0 = time.perf_counter()
    asyncio.run(_run())
    return time.perf_counter() - t0


def main():
    print(f"{N} 个任务，每个等 {WAIT}s   →   串行应该 ≈ {N * WAIT:.1f}s")
    print()

    results = [
        ("① 串行      ", run_serial(wait_task, N)),
        ("② 线程池(8) ", run_thread(wait_task, N)),
        ("③ 进程池(8) ", run_process(wait_task, N)),
        ("④ asyncio   ", run_async(async_wait_task, N)),
    ]
    base = results[0][1]
    for label, t in results:
        print(f"  {label} {t:6.2f}s   加速 {base / t:4.1f}x")


if __name__ == "__main__":              # ⚠️ 进程池必须
    main()
