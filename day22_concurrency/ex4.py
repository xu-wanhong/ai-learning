from concurrent.futures import ThreadPoolExecutor, as_completed


def work(n):
    return n * 10


with ThreadPoolExecutor(max_workers=3) as ex:
    futures = [ex.submit(work, i) for i in [1, 2, 3]]
    for f in futures:
        print(f.result())