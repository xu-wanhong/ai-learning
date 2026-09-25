import time
import httpx

URL = "http://127.0.0.1:8765/page1"

httpx.get(URL, timeout=10)              # 热身

t0 = time.perf_counter()
r = httpx.get(URL, timeout=10)
print(r.status_code, f"{time.perf_counter() - t0:.2f}s")