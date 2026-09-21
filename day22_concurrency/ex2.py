import time
from concurrent.futures import ThreadPoolExecutor


def work(n):
    time.sleep(1)          # 模拟等待：网络请求、数据库都算
    return n


# ---- 串行：一个一个来 ----
start = time.perf_counter()
for i in [1, 2, 3]:
    work(i)
serial = time.perf_counter() - start
print(f"串行:   {serial:.2f} 秒")


# ---- 并发：三个一起 ----
start = time.perf_counter()
with ThreadPoolExecutor(max_workers=1) as ex:
    list(ex.map(work, [1, 2, 3]))
concurrent = time.perf_counter() - start
print(f"线程池: {concurrent:.2f} 秒")