"""Day 39 · 题2 —— 分页依赖

好处：10 个列表接口都写 `Depends(pagination)` 就行，
      不用每个都写 page/size/skip/limit 那堆参数。

启动：
    cd ~/dev/ai-learning/day39_depends
    ../.venv/bin/python -m uvicorn pagination_app:app --port 8000

测试：
    curl http://127.0.0.1:8000/items
    curl "http://127.0.0.1:8000/items?page=3&size=20"
    curl "http://127.0.0.1:8000/items?size=500"
"""
from fastapi import Depends, FastAPI, Query

app = FastAPI(title="Day 39 · 题2 分页依赖")


# ============ 依赖函数：算分页参数 ============
def pagination(
    page: int = Query(default=1, ge=1, description="第几页，从 1 开始"),
    size: int = Query(default=10, ge=1, le=100, description="每页几条，最多 100"),
):
    """返回给接口用的分页信息"""
    return {
        "page": page,
        "size": size,
        "skip": (page - 1) * size,      # 数据库里跳过多少条
        "limit": size,                   # 最多取多少条
    }


# ============ 接口 1：只要分页 ============
@app.get("/items")
def list_items(p: dict = Depends(pagination)):
    return p


# ============ 接口 2：真实用法（假装在查数据库）============
FAKE_DB = [f"第 {i} 条数据" for i in range(1, 101)]      # 100 条假数据


@app.get("/users")
def list_users(p: dict = Depends(pagination)):
    """把 skip / limit 用在切片上，就是真正的分页"""
    page_data = FAKE_DB[p["skip"] : p["skip"] + p["limit"]]
    return {
        "总数": len(FAKE_DB),
        "第几页": p["page"],
        "每页": p["size"],
        "这一页的数据": page_data,
    }


# ============ 接口 3：分页 + 关键词过滤 ============
@app.get("/search")
def search(p: dict = Depends(pagination), q: str = ""):
    matched = [x for x in FAKE_DB if q in x]
    return {
        "关键词": q,
        "匹配总数": len(matched),
        "这一页": matched[p["skip"] : p["skip"] + p["limit"]],
    }
