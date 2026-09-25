import time

import httpx

BASE = "http://127.0.0.1:8765"

t0 = time.perf_counter()
with httpx.Client(timeout=10) as client:
    for i in range(10):
        r = client.get(f"{BASE}/page{i}")
        print(f"page{i} → {r.status_code}")
print(f"同步串行 10 个请求：{time.perf_counter() - t0:.2f}s")