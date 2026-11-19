"""Day 39 · 题3 —— 依赖套依赖（三层鉴权）

这是真实项目的标准写法，每一层只管一件事：

    第 1 层  verify_token    有没有带 token？          → 401
    第 2 层  current_user    这个 token 是哪个用户？    → 401
    第 3 层  require_admin   这个用户是不是管理员？      → 403

好处：接口想要哪一层，就 Depends 哪一层。

    /me              → Depends(current_user)    普通用户就能看
    /admin/dashboard → Depends(require_admin)   必须管理员

启动：
    cd ~/dev/ai-learning/day39_depends
    ../.venv/bin/python -m uvicorn auth_app:app --port 8000
"""
from fastapi import Depends, FastAPI, Header, HTTPException

app = FastAPI(title="Day 39 · 题3 三层鉴权")


# 假装是数据库：token → 用户信息
USERS = {
    "Bearer tom-token":   {"name": "tom",   "role": "user"},
    "Bearer admin-token": {"name": "admin", "role": "admin"},
}


# ============ 第 1 层：有没有 token ============
def verify_token(authorization: str | None = Header(default=None)):
    if authorization is None:
        raise HTTPException(status_code=401, detail="没带 token")
    return authorization


# ============ 第 2 层：这个 token 是哪个用户 ============
def current_user(token: str = Depends(verify_token)):
    user = USERS.get(token)
    if user is None:
        raise HTTPException(status_code=401, detail="token 无效")
    return user


# ============ 第 3 层：是不是管理员 ============
def require_admin(user: dict = Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail=f"需要管理员权限，你是 {user['role']}",
        )
    return user


# ============ 接口 1：只要登录（2 层）============
@app.get("/me")
def me(user: dict = Depends(current_user)):
    return {"msg": f"你好 {user['name']}", "你的角色": user["role"]}


# ============ 接口 2：必须是管理员（3 层）============
@app.get("/admin/dashboard")
def dashboard(admin: dict = Depends(require_admin)):
    return {"msg": f"欢迎管理员 {admin['name']}", "dashboard": "这里是后台数据"}


# ============ 接口 3：公开 ============
@app.get("/public")
def public():
    return {"msg": "谁都能看"}
