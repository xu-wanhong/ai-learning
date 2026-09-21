from concurrent.futures import ProcessPoolExecutor


def work(n):
    return n * n


if __name__ == "__main__":          # ⚠️ 这行不能省！
    with ProcessPoolExecutor(max_workers=2) as ex:
        print(list(ex.map(work, [1, 2, 3, 4])))