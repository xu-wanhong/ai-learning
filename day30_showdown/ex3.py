# ex3 · 进程池的启动开销：任务越小，越亏

import itertools
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

N = 8
WORKERS = 8
SIZES = [200_000, 2_000_000, 10_000_000]


def cpu_loop(i, loops):
    """模块级函数（进程池的硬性要求）"""
    total = 0
    for k in range(loops):
        total += k * k
    return total


def main():
    print("=" * 76)
    print("进程池的启动开销：任务越小，加速比越差")
    print("=" * 76)
    print(f"{'单个任务规模':>14} | {'串行':>8} | {'线程池(8)':>10} | {'进程池(8)':>10} | {'进程加速比':>9}")
    print("-" * 76)

    for loops in SIZES:
        # ---- 串行 ----
        t0 = time.perf_counter()
        for i in range(N):
            cpu_loop(i, loops)
        serial = time.perf_counter() - t0

        # ---- 线程池 ----
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            list(ex.map(cpu_loop, range(N), itertools.repeat(loops)))
        thread = time.perf_counter() - t0

        # ---- 进程池（注意：计时从提交开始，启动开销算在里面）----
        with ProcessPoolExecutor(max_workers=WORKERS) as ex:
            t0 = time.perf_counter()
            list(ex.map(cpu_loop, range(N), itertools.repeat(loops)))
            process = time.perf_counter() - t0

        print(f"{loops:>14,} | {serial:7.3f}s | {thread:9.3f}s | {process:9.3f}s | {serial / process:8.2f}x")


if __name__ == "__main__":
    main()
