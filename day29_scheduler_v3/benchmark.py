"""benchmark · 不重试 vs 重试（Day 29 最有说服力的一张表）

8 个任务，每个 1 秒；其中第 3 和第 6 个「前 2 次会失败」。

    不重试（max_retry=0）: 成功 6 / 失败 2   耗时 1.00s   总请求次数 8
    重试（max_retry=3）  : 成功 8 / 失败 0   耗时 3.31s   总请求次数 12

【三组对比】
                    不重试        重试        变化
    成功率          6/8 = 75%     8/8 = 100%  ⬆️ 收益
    耗时            1.00s         3.31s       ⬆️ 3.3 倍
    对下游请求量    8 次          12 次       ⬆️ +50%

【结论】重试不是免费的。
    把成功率从 75% 拉到 100%，代价是 3.3 倍耗时 + 对下游多 50% 的压力。

【所以"重试几次"是业务决策】
    · 用户在等（网页请求）   → 重试要【少、快】
    · 后台批量任务           → 可以【多试几次】
    · 下游已经快挂了         → 重试会【加速它死亡】（重试雪崩）

这也正是必须「指数退避」的原因：所有任务同时重试 = 同时给下游一波新的压力。
"""
import asyncio
import time

DUR = [1, 1, 1, 1, 1, 1, 1, 1]
FAIL_TIMES = [0, 0, 2, 0, 0, 2, 0, 0]        # 第 3 和第 6 个：前 2 次失败
BASE = 0.1


async def flaky(i, attempts):
    attempts[i] = attempts.get(i, 0) + 1
    n = attempts[i]
    await asyncio.sleep(DUR[i])
    if n <= FAIL_TIMES[i]:
        raise ValueError(f"task_{i} 第 {n} 次失败")
    return f"task_{i} 第 {n} 次成功"


async def run(max_retry):
    attempts = {}
    ok, bad = 0, 0
    t0 = time.perf_counter()

    async def one(i):
        nonlocal ok, bad
        for k in range(max_retry + 1):
            try:
                await flaky(i, attempts)
                ok += 1
                return
            except ValueError:
                if k == max_retry:
                    bad += 1
                    return
                await asyncio.sleep(BASE * (2 ** k))     # 指数退避

    await asyncio.gather(*(one(i) for i in range(8)))
    return ok, bad, time.perf_counter() - t0, sum(attempts.values())


async def main():
    print(f"8 个任务，每个 {DUR[0]}s；第 3 和第 6 个「前 2 次会失败」\n")

    ok, bad, t, total = await run(0)
    print(f"不重试（max_retry=0）: 成功 {ok} / 失败 {bad}   耗时 {t:.2f}s   总请求次数 {total}")

    ok, bad, t, total = await run(3)
    print(f"重试（max_retry=3）  : 成功 {ok} / 失败 {bad}   耗时 {t:.2f}s   总请求次数 {total}")


asyncio.run(main())
