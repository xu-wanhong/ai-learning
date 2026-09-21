"""Day 22 实验：线程池 vs 进程池 vs 串行"""
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


def cpu_task(n: int) -> int:
    """CPU 密集型：纯计算，不放 GIL"""
    total = 0
    for i in range(n):
        total += i * i
    return total


def io_task(seconds: float) -> float:
    """I/O 密集型：sleep 期间会释放 GIL"""
    time.sleep(seconds)
    return seconds


def run_serial(func, args_list):
    start = time.perf_counter()
    for a in args_list:
        func(a)
    return time.perf_counter() - start


def run_threads(func, args_list, workers=4):
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(func, args_list))
    return time.perf_counter() - start


def run_processes(func, args_list, workers=4):
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        list(ex.map(func, args_list))
    return time.perf_counter() - start


def report(title, args_list, func):
    print("=" * 58)
    print(title)
    print("=" * 58)
    s = run_serial(func, args_list)
    t = run_threads(func, args_list)
    p = run_processes(func, args_list)
    print(f"  串行        : {s:6.2f}s")
    print(f"  线程池(4)   : {t:6.2f}s   加速比 {s/t:5.2f}x")
    print(f"  进程池(4)   : {p:6.2f}s   加速比 {s/p:5.2f}x")
    print()


if __name__ == "__main__":
    N = 20000000
    report("实验 A：CPU 密集型（4 个计算任务）", [N] * 4, cpu_task)
    report("实验 B：I/O 密集型（4 个各等 1 秒）", [1.0] * 4, io_task)
        