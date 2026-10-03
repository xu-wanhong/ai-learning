"""ex4 · 混合场景：既有「等」又有「算
"""
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

N_TASKS = 16
WORKERS = 4
IO_TIME = 0.3
CPU_LOOPS = 9_500_000          # ≈ 0.20s


# ---------------- 任务定义（模块级！）----------------
def cpu_part():
    """纯计算部分"""
    total = 0
    for k in range(CPU_LOOPS):
        total += k * k
    return total


def mixed_sync(i):
    """A / B 用：等 + 算 都塞在一个函数里"""
    time.sleep(IO_TIME)
    return cpu_part()


def cpu_only(i):
    """C 用：只算（会被丢给进程池）"""
    return cpu_part()


async def async_mixed(i, pool):
    """C：等用协程，算丢进程池"""
    await asyncio.sleep(IO_TIME)                              # ① I/O：协程并发
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(pool, cpu_only, i)      # ② CPU：进程池并行


# ---------------- 三种跑法 ----------------
def plan_a():
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(mixed_sync, range(N_TASKS)))
    return time.perf_counter() - t0


def plan_b():
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        t0 = time.perf_counter()
        list(ex.map(mixed_sync, range(N_TASKS)))
        return time.perf_counter() - t0


def plan_c():
    async def _run(pool):
        await asyncio.gather(*(async_mixed(i, pool) for i in range(N_TASKS)))

    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        t0 = time.perf_counter()
        asyncio.run(_run(pool))
        return time.perf_counter() - t0


def main():
    print(f"{N_TASKS} 个任务 · {WORKERS} 个工人 · 每个「先等 {IO_TIME}s，再算 ≈0.2s」\n")

    a = plan_a()
    print(f"  A. 全用线程池({WORKERS})     : {a:5.2f}s")
    b = plan_b()
    print(f"  B. 全用进程池({WORKERS})     : {b:5.2f}s")
    c = plan_c()
    print(f"  C. asyncio + 进程池      : {c:5.2f}s   ← 最快")

    print()
    print("  为什么：")
    print(f"    A 慢在哪：CPU 部分 {N_TASKS} × 0.2s = {N_TASKS * 0.2:.1f}s 全部串行（GIL 不让路）")
    print(f"    B 慢在哪：每个工人「等 {IO_TIME} + 算 0.2」串着做，{N_TASKS // WORKERS} 轮"
          f" = {(IO_TIME + 0.2) * (N_TASKS // WORKERS):.1f}s")
    print(f"    C 快在哪：等 → 全部并发 {IO_TIME}s；算 → 丢进程池 {N_TASKS}×0.2/{WORKERS}"
          f" = {N_TASKS * 0.2 / WORKERS:.1f}s")
    print("              —— 「等」和「算」被【拆开分别并行】了")


if __name__ == "__main__":
    main()
