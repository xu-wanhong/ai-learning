"""Day 39 · 题1 —— 用 Depends 做鉴权

对比两种写法：不写 Depends 会重复几行；写了只一行。
"""
from fastapi import Depends, FastAPI, Header, HTTPException

app = FastAPI(title="Day 39 · 题1 鉴权")

ADMIN_TOKEN = "Bearer admin-token"


# ============ ✅ 依赖函数：检查 token ============
def verify_admin(authorization: str | None = Header(default=None)):
    """没带或不对 → 401。对了 → 把 token 返回给接口用。"""
    if authorization != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="token 不对或没带")
    return authorization


# ============ 接口 1：用 Depends（推荐）============
@app.get("/admin")
def admin(token: str = Depends(verify_admin)):
    return {"msg": "欢迎管理员", "你带的": token}


# ============ 接口 2：不用 Depends（对照，看重复）============
@app.get("/admin-copy")
def admin_copy(authorization: str | None = Header(default=None)):
    if authorization != ADMIN_TOKEN:                          # ← 重复
        raise HTTPException(status_code=401, detail="token 不对或没带")
    return {"msg": "欢迎管理员（复制版）", "你带的": authorization}


# ============ 接口 3：第三个接口，同样要登录 ============
@app.get("/admin/orders")
def admin_orders(token: str = Depends(verify_admin)):
    return {"msg": "订单列表", "管理员": token}


# ============ 排错用：把收到的 header 原样吐出来 ============
@app.get("/debug-auth")
def debug_auth(authorization: str | None = Header(default=None)):
    return {
        "你实际发的": authorization,
        "应该是": ADMIN_TOKEN,
        "一样吗": authorization == ADMIN_TOKEN,
        "你的长度": len(authorization) if authorization else 0,
        "应该的长度": len(ADMIN_TOKEN),
        "你的字符": [c for c in (authorization or "")],
    }


# ============ 对照实验：换一个 header 名字 ============
# 如果这个在 Swagger 里能填通，就说明 authorization 这个名字被 Swagger 特殊处理了
@app.get("/debug-x")
def debug_x(x_admin_token: str | None = Header(default=None)):
    return {
        "收到的 x-admin-token": x_admin_token,
        "一样吗": x_admin_token == "admin-token",
    }


@app.get("/admin-x")
def admin_x(x_admin_token: str | None = Header(default=None)):
    if x_admin_token != "admin-token":
        raise HTTPException(status_code=401, detail="x-admin-token 不对或没带")
    return {"msg": "欢迎管理员（用 x-admin-token）"}
