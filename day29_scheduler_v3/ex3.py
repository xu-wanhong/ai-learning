"""ex3 · 重试 + 指数退避

在 ex2 基础上多一层：失败了【等一会儿再来】，而且等待时间逐次翻倍。

    第 1 次失败 → 等 0.1s
    第 2 次失败 → 等 0.2s
    第 3 次失败 → 等 0.4s

【为什么必须翻倍】
如果所有失败的任务都"等 1 秒再试"，它们会【同时】又去打下游一次 ——
下游刚缓过来又被一波打死，这叫「重试雪崩」。
翻倍能让它们的重试时间【错开】。

【核心代码只有 8 行】
    for i in range(MAX_RETRY + 1):
        try:
            return await 任务()
        except 可重试的错误 as e:
            if i == MAX_RETRY:      # 最后一次，放弃
                raise
            await asyncio.sleep(BASE * (2 ** i))
"""
import asyncio

BASE = 0.1
MAX_RETRY = 3
attempts = {}


async def flaky(tid, fail_times):
    """前 fail_times 次失败，之后成功"""
    n = attempts.get(tid, 0) + 1
    attempts[tid] = n
    await asyncio.sleep(0.05)
    if n <= fail_times:
        raise ValueError(f"第 {n} 次尝试失败")
    return f"第 {n} 次成功"


async def with_retry(tid, fail_times):
    for i in range(MAX_RETRY + 1):
        try:
            return await flaky(tid, fail_times)
        except ValueError as e:
            if i == MAX_RETRY:
                raise
            delay = BASE * (2 ** i)
            print(f"    重试 {tid}：{e} → 等 {delay:.1f}s 后第 {i + 2} 次")
            await asyncio.sleep(delay)


async def main():
    print("A) 前 2 次失败、第 3 次成功：")
    r = await with_retry("A", fail_times=2)
    print(f"   最终：✅ {r}（共试了 {attempts['A']} 次）")

    print()
    print("B) 每次都失败（重试 3 次后放弃）：")
    try:
        await with_retry("B", fail_times=99)
    except ValueError as e:
        print(f"   最终：❌ {e}（共试了 {attempts['B']} 次）")

    print()
    print("退避时间表（BASE = 0.1）：")
    for i in range(MAX_RETRY):
        print(f"    第 {i + 1} 次失败后等 {BASE * (2 ** i):.1f}s")


asyncio.run(main())
