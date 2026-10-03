"""ex2 · GIL 的直接证明
"""
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

N = 8
SLEEP = 0.3
CPU_LOOPS = 14_000_000         # ≈ 0.30s 纯算术
SPIN_LOOPS = 23_000_000        # ≈ 0.50s 纯算术
WORKERS = 8


def wait_task(i):
    """等 0.3 秒 —— sleep 会【主动释放 GIL】"""
    time.sleep(SLEEP)
    return i


def cpu_task(i):
    """烧 0.3 秒 CPU —— 计算【不会让出 GIL】"""
    total = 0
    for k in range(CPU_LOOPS):
        total += k * k
    return total


def burn(i):
    """纯算术忙等（给实验②用）"""
    x = 0
    for k in range(SPIN_LOOPS):
        x += k * k
    return x


def run_serial(fn):
    t0 = time.perf_counter()
    for i in range(N):
        fn(i)
    return time.perf_counter() - t0


def run_thread(fn, n=N, workers=WORKERS):
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(fn, range(n)))
    return time.perf_counter() - t0


def run_process(fn, n=N, workers=WORKERS):
    with ProcessPoolExecutor(max_workers=workers) as ex:
        t0 = time.perf_counter()
        list(ex.map(fn, range(n)))
        return time.perf_counter() - t0


def main():
    print("=" * 68)
    print("实验 ①：同样忙 0.3 秒，一个在「等」、一个在「算」")
    print("=" * 68)
    print(f"{'任务类型':>18} | {'串行':>8} | {'线程池(8)':>14} | {'进程池(8)':>14}")
    print("-" * 68)
    for label, fn in [("等待型 time.sleep", wait_task), ("计算型 纯算术", cpu_task)]:
        s = run_serial(fn)
        th = run_thread(fn)
        pr = run_process(fn)
        print(f"{label:>18} | {s:7.2f}s | {th:8.2f}s  {s/th:4.1f}x | {pr:8.2f}s  {s/pr:4.1f}x")

    print()
    print("=" * 68)
    print("实验 ②：两个纯 CPU 循环同时跑（每个 ≈ 0.5s）")
    print("=" * 68)
    t0 = time.perf_counter()
    burn(0); burn(1)
    print(f"  串行             : {time.perf_counter() - t0:.2f}s")

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(burn, range(2)))
    print(f"  2 个线程同时跑   : {time.perf_counter() - t0:.2f}s   ← 【没有变快！GIL 在排队】")

    with ProcessPoolExecutor(max_workers=2) as ex:
        t0 = time.perf_counter()
        list(ex.map(burn, range(2)))
        print(f"  2 个进程同时跑   : {time.perf_counter() - t0:.2f}s   ← 真并行")


if __name__ == "__main__":
    main()
