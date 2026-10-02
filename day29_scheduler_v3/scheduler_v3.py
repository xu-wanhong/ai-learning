import asyncio
import time 
import json


TASKS = [
    ("TASK-001", "tom",  3, "ok"),
    ("TASK-002", "jack", 1, "ok"),
    ("TASK-003", "rose", 4, "always"),
    ("TASK-004", "lucy", 2, "ok"),
    ("TASK-005", "bob",  1, "ok"),
    ("TASK-006", "amy",  2, "flaky"),
    ("TASK-007", "ken", 10, "hang"),
    ("TASK-008", "zoe",  2, "ok"),
]

attempts = {}
MAX_CONCURRENT=3
MAX_RETRY=2
TIMEOUT=4
RETRY_BASE=0.1

async def ai_task(task_id,name,seconds,mode):
    n=attempts.get(task_id,0)+1
    attempts[task_id]=n
    if mode=="always":
        await asyncio.sleep(0.2)
        raise ValueError(f"{name} 服务端错误")
    if mode=="flaky" and n<=2:
        await asyncio.sleep(0.2)
        raise ValueError(f"{name}第{n}次尝试失败")

    await asyncio.sleep(seconds)
    return f"{name}执行成功，第{n}次尝试"

async def run_with_retry(task_id,name,seconds,mode):
    for i in range(MAX_RETRY+1):
        try:
            return await asyncio.wait_for(ai_task(task_id,name,seconds,mode),
                                          timeout=TIMEOUT)
        except(ValueError,TimeoutError)as e:
            if i==MAX_RETRY:
                if isinstance(e,TimeoutError):
                    raise  TimeoutError (f"连续{MAX_RETRY+1}次失败 超时{TIMEOUT}s")
                raise
            delay=RETRY_BASE*(2**i)
            dec=f"超时{TIMEOUT}s" if isinstance(e,TimeoutError)  else str(e)
            print(f"{task_id}重试 :错误类型{type(e).__name__} 等{delay:.1f}s后 第{i+2}次尝试 ")
            await asyncio.sleep(delay)


async def main():
    sem=asyncio.Semaphore(MAX_CONCURRENT)
    results = {}
    success = 0
    failed = 0
    t0 = time.perf_counter()

    async def limited(ta,na,se,mo):
        async with sem:
            return await run_with_retry(ta,na,se,mo)

    future_map={}
    for ta,na,se,mo in TASKS:
        task=asyncio.create_task(limited(ta,na,se,mo))
        future_map[task]=(ta,na)
    async for f in asyncio.as_completed(future_map):
        task_id,name=future_map[f]
        try:
            result=await f
            success+=1
            results[task_id]={"name":name, "status":"success" ,
                              "attempts":attempts.get(task_id,0) ,
                              "result":result}
            print(f"{task_id} | {name} | success |尝试了{attempts.get(task_id,0)}次")
        
        except(ValueError,TimeoutError)as e:
            failed+=1
            results[task_id]={"name":name, "status":"failed" ,
                              "attempts":attempts.get(task_id,0) ,
                              "error": f"{type(e).__name__} {e}"}
            print(f"{task_id} | {name} | failed |尝试了{attempts.get(task_id,0)}次 | {e}")
    t1=time.perf_counter()-t0
    print(f"成功{success}  失败{failed}  总耗时{t1:.2f}s")
    with open("results.json","w",encoding="utf-8")as fp:
        json.dump(results, fp, ensure_ascii=False, indent=2)
    print(f"结果已写入 results.json（{len(results)} 项）")


asyncio.run(main())

