"""benchmark · Day 30 终局总表：2 种任务 × 4 种跑法

实测（10 核 · 8 个任务 · 8 个工人；每次跑有 ±10% 波动）：

【等待型】每个 time.sleep(0.3)    串行基准 ≈ 2.4s
  ① 串行          2.44s   ──── 基准 ────
  ② 线程池(8)     0.31s   加速   8.0x
  ③ 进程池(8)     0.39s   加速   6.2x
  ④ asyncio       0.30s   加速   8.1x

【计算型】每个循环 10,000,000 次
  ① 串行          1.78s   ──── 基准 ────
  ② 线程池(8)     1.63s   加速   1.1x     ← GIL 卡死
  ③ 进程池(8)     0.48s   加速   3.7x     ← 真并行
  ④ asyncio       1.65s   加速   1.1x     ← 协程不能算

【怎么读这张表】
                    线程池      进程池      asyncio
    等待型（等 I/O）  8.0x ✅    6.2x（浪费） 8.1x ✅
    计算型（烧 CPU）  1.1x ❌    3.7x ✅      1.1x ❌

    两个 1.1x = GIL 和「协程不能算」的铁证
    两个 8x   = 「等待时可以并发」的铁证

⚠️ 进程池的任务函数必须是【模块级函数】；全部逻辑要在 __main__ 保护里。
"""
import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

N_TASKS = 8
WAIT = 0.3
CPU_LOOPS = 10_000_000
WORKERS = 8


# ---------------- 任务定义（模块级！）----------------
def wait_task(i):
    """等待型（模拟 I/O）—— 线程池 / 进程池用"""
    time.sleep(WAIT)
    return i


async def async_wait_task(i):
    """等待型 —— asyncio 用"""
    await asyncio.sleep(WAIT)
    return i


def cpu_task(i):
    """计算型（真的烧 CPU）"""
    total = 0
    for k in range(CPU_LOOPS):
        total += k * k
    return total


async def async_cpu_task(i):
    """asyncio 里【没法】并行做 CPU 计算 —— 直接调会按住事件循环，等于串行。
    这本身就是结论，不是 bug。"""
    return cpu_task(i)


# ---------------- 四种跑法 ----------------
def run_serial(fn):
    t0 = time.perf_counter()
    for i in range(N_TASKS):
        fn(i)
    return time.perf_counter() - t0


def run_thread(fn):
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(fn, range(N_TASKS)))
    return time.perf_counter() - t0


def run_process(fn):
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        t0 = time.perf_counter()
        list(ex.map(fn, range(N_TASKS)))
        return time.perf_counter() - t0


def run_async(coro_fn):
    async def _run():
        await asyncio.gather(*(coro_fn(i) for i in range(N_TASKS)))

    t0 = time.perf_counter()
    asyncio.run(_run())
    return time.perf_counter() - t0


def main():
    print(f"机器 {os.cpu_count()} 核 · 任务数 {N_TASKS} · 工人数 {WORKERS}\n")

    cases = [
        (f"【等待型】每个 time.sleep({WAIT})", wait_task, async_wait_task,
         f"串行基准 ≈ {N_TASKS * WAIT:.1f}s"),
        (f"【计算型】每个循环 {CPU_LOOPS:,} 次", cpu_task, async_cpu_task, ""),
    ]

    for title, fn, afn, note in cases:
        print("=" * 66)
        print(f"{title}    {note}")
        print("=" * 66)
        base = run_serial(fn)
        print(f"  ① 串行        {base:6.2f}s   ──── 基准 ────")
        t = run_thread(fn)
        print(f"  ② 线程池(8)   {t:6.2f}s   加速 {base / t:5.1f}x")
        t = run_process(fn)
        print(f"  ③ 进程池(8)   {t:6.2f}s   加速 {base / t:5.1f}x")
        t = run_async(afn)
        print(f"  ④ asyncio     {t:6.2f}s   加速 {base / t:5.1f}x")
        print()


if __name__ == "__main__":
    main()
