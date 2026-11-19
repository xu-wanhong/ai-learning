# Day 39 · `Depends`（依赖注入）

2026-11-19 · macOS · FastAPI 0.162.0

> **一句话：告诉 FastAPI「这个参数你别让用户传，你帮我准备好」。**
>
> **这是鉴权、数据库连接、分页的标准写法。**

---

## 一、先看问题（不用 `Depends` 会怎样）

**服务有 5 个接口，其中 3 个需要登录。**

**不用 `Depends`**：

```python
@app.get("/me")
def me(authorization: str | None = Header(default=None)):
    if authorization != TOKEN:                    # ← 重复 1
        raise HTTPException(401, "token 不对")
    return {...}

@app.get("/items")
def items(authorization: str | None = Header(default=None)):
    if authorization != TOKEN:                    # ← 重复 2
        raise HTTPException(401, "token 不对")
    return {...}

@app.get("/orders")
def orders(authorization: str | None = Header(default=None)):
    if authorization != TOKEN:                    # ← 重复 3
        raise HTTPException(401, "token 不对")
    return {...}
```

| 问题 | 后果 |
|---|---|
| 同一段代码抄 3 遍 | 改成 JWT 之后要改 3 处，**漏一个就出安全漏洞** |
| 每个接口都得写 | 新增接口忘了写 = 漏洞 |
| 文档里看不出"要登录" | `/docs` 里只有参数，没标语义 |

**用 `Depends`**：

```python
def verify_admin(authorization: str | None = Header(default=None)):
    if authorization != ADMIN_TOKEN:
        raise HTTPException(401, "token 不对或没带")
    return authorization


@app.get("/admin")
def admin(token: str = Depends(verify_admin)):      # ← 就这一行
    return {"msg": "欢迎管理员", "你带的": token}
```

---

## 二、`Depends` 到底做了什么（三件事）

```python
token: str = Depends(verify_admin)
#      │      └──────┬───────┘
#    拿到返回值    调这个函数（⚠️ 不加括号）
```

| 它做的事 | 效果 |
|---|---|
| **① 调 `verify_admin()`** | token 不对 → **自动 401**，**接口函数根本不会执行** |
| **② 把返回值塞进 `token`** | 你能直接用 |
| **③ 把依赖函数的参数合并进 `/docs`** | 文档里自动出现 `authorization` |

---

## 三、用法 1 · 单个依赖（鉴权）

```python
ADMIN_TOKEN = "Bearer admin-token"


def verify_admin(authorization: str | None = Header(default=None)):
    if authorization != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="token 不对或没带")
    return authorization


@app.get("/admin")
def admin(token: str = Depends(verify_admin)):
    return {"msg": "欢迎管理员", "你带的": token}
```

**实测**：

```
curl /admin（不带 token）                           → [401] token 不对或没带
curl -H 'Authorization: Bearer wrong' /admin        → [401] token 不对或没带
curl -H 'Authorization: Bearer admin-token' /admin  → [200] {"msg":"欢迎管理员",...}
```

> **401 的时候，`admin()` 函数里的代码一行都没跑** —— 依赖先把门拦住了。

---

## 四、用法 2 · 参数依赖（分页）

**问题**：10 个列表接口都要 `page` / `size`，每个都写一遍。

**解法**：

```python
from fastapi import Query


def pagination(
    page: int = Query(default=1, ge=1, description="第几页"),
    size: int = Query(default=10, ge=1, le=100, description="每页几条"),
):
    return {
        "page": page,
        "size": size,
        "skip": (page - 1) * size,      # 数据库里跳过多少条
        "limit": size,                   # 最多取多少条
    }


@app.get("/items")
def list_items(p: dict = Depends(pagination)):
    return p
```

**实测**：

```
无参数               → {"page":1,"size":10,"skip":0,"limit":10}
?page=3&size=20      → {"page":3,"size":20,"skip":40,"limit":20}
?size=500（超过100）  → 422  less_than_equal: size ≤ 100
?page=0（小于1）      → 422  greater_than_equal: page ≥ 1
?size=100（刚好上限） → 200
```

### ⭐ `skip` 为什么是 `(page - 1) * size`

**页码从 1 开始，但数组索引从 0 开始。**

| 第几页 | 每页几条 | 跳过几条 | 算式 |
|---|---|---|---|
| 1 | 10 | **0** | `(1-1)×10` |
| 2 | 10 | **10** | `(2-1)×10` |
| 3 | 10 | **20** | `(3-1)×10` |
| 2 | 3 | **3** | `(2-1)×3` |

**画出来（每页 3 条）**：

```
数据：   [第1条] [第2条] [第3条] │ [第4条] [第5条] [第6条] │ [第7条]
索引：      0       1       2    │    3       4       5    │    6
                                 └──── FAKE_DB[3:6] ───────┘
                                      第 2 页（size=3）
```

**真实用法**：

```python
FAKE_DB[p["skip"] : p["skip"] + p["limit"]]
```

**接数据库后（B1 阶段）会变成**：

```python
db.query(User).offset(p["skip"]).limit(p["limit"]).all()
```

**或者 SQL**：

```sql
SELECT * FROM users LIMIT 3 OFFSET 3;
```

> **`OFFSET` = `skip`，`LIMIT` = `limit`。你现在手算的，就是数据库在做的事。**

### `Query()` vs `Field()`

| | 管什么 |
|---|---|
| **`Query(...)`** | **查询参数**（`?page=1`） |
| **`Field(...)`** | **请求体字段**（JSON 里的） |

**约束参数一样**：`ge` / `le` / `min_length` / `max_length` / `description`。

---

## 五、用法 3 · ⭐ 依赖套依赖（三层鉴权）

**真实项目的标准写法，每一层只管一件事。**

```python
# 第 1 层：有没有 token
def verify_token(authorization: str | None = Header(default=None)):
    if authorization is None:
        raise HTTPException(status_code=401, detail="没带 token")
    return authorization


# 第 2 层：这个 token 是哪个用户
def current_user(token: str = Depends(verify_token)):
    user = USERS.get(token)              # 查不到给 None（不报错）
    if user is None:
        raise HTTPException(status_code=401, detail="token 无效")
    return user


# 第 3 层：是不是管理员
def require_admin(user: dict = Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail=f"需要管理员权限，你是 {user['role']}")
    return user


@app.get("/me")
def me(user: dict = Depends(current_user)):        # ← 只要 2 层
    return {"msg": f"你好 {user['name']}", "你的角色": user["role"]}


@app.get("/admin/dashboard")
def dashboard(admin: dict = Depends(require_admin)):    # ← 要 3 层
    return {"msg": f"欢迎管理员 {admin['name']}"}
```

### 执行顺序（从下往上调用，从上往下返回）

```
请求进来
  → dashboard 要 require_admin
      → require_admin 要 current_user
          → current_user 要 verify_token
              → verify_token 取 header
          ← 返回 token
      ← 返回 user
  ← 返回 admin
→ 执行 dashboard 函数体
```

### 实测：四道关卡

| 请求 | 结果 | 卡在 |
|---|---|---|
| **不带 token** | `401 没带 token` | 第 1 层 |
| **`Bearer wrong`** | `401 token 无效` | 第 2 层 |
| **`Bearer tom-token`** | **`403 需要管理员权限，你是 user`** | 第 3 层 |
| **`Bearer admin-token`** | **`200 欢迎管理员 admin`** | 全过 |

> **三条错误消息各不相同** —— 出问题一眼知道是哪一关。

---

## 六、⭐ 401 vs 403（**面试会问**）

| 码 | 意思 | 什么时候用 |
|---|---|---|
| **401** | **你是谁？**（没认证） | 没带 token / token 无效 → **"去登录"** |
| **403** | **我知道你是谁，但你不够格** | tom 登录了但不是管理员 → **"去申请权限"** |

```
token 无效   → 401   ← 我不认识你
tom 的 token → 403   ← 我认识你（tom），但你不是 admin
```

---

## 七、⭐ 最直观的证据：`/docs` 里参数自动合并

**实测（三个接口的参数列表）**：

```
GET /public          参数: []                                  ← 无依赖
GET /me              参数: ['authorization']                   ← 来自 verify_token
GET /items           参数: ['page', 'size', 'authorization']    ← 来自两个依赖
GET /public-items    参数: ['page', 'size']                    ← 来自 pagination
```

**`/items` 的签名**：

```python
def list_items(user = Depends(current_user), p = Depends(pagination)):
```

**它自己一个参数都没写** —— 但 `/docs` 里出现了 **3 个参数**。

> **FastAPI 把依赖里的参数"摊平"合并进来了。**

---

## 八、`Depends` 和"直接调用函数"的区别

```python
# ❌ 直接调用（会报错：缺 authorization 参数）
@app.get("/me")
def me():
    token = verify_token()
    return {"token": token}

# ✅ Depends
@app.get("/me")
def me(token: str = Depends(verify_token)):
    return {"token": token}
```

| | 直接调用 | `Depends` |
|---|---|---|
| 参数从哪来 | 你得自己传 | **FastAPI 从请求里取** |
| 在 `/docs` 里体现吗 | ❌ | ✅ |
| 能提前拦截吗 | 要自己写 `if` | ✅ 抛异常就拦住 |

---

## 九、踩的坑

| # | 坑 | 后果 |
|---|---|---|
| **1** | **`Depends(函数())` 加了括号** | **现在就调用了**，然后传返回值 → 报错 |
| **2** | 依赖函数**忘了 `return`** | 接口里拿到 `None` |
| **3** | 依赖里抛的异常被 `try/except` 捕获 | **不会** —— 它直接返回给客户端，不经过接口函数 |
| **4** | 依赖里做耗时操作（连数据库） | **每个请求跑一次** → 要用 `yield`（Day 40 讲） |
| **5** | 用 `Header()` 不带 `default` | 不带 header 时返回 **422**（参数校验失败），而不是 401 |

### 坑 5 详解

```python
# ❌ 必填 → 不带就 422
def verify(authorization: str = Header()):
    ...

# ✅ 可选 → 不带就是 None → 自己判断 → 401
def verify(authorization: str | None = Header(default=None)):
    if authorization is None:
        raise HTTPException(401, "请先登录")
```

**"没登录"应该是 401，不是 422。**

---

## 十、`dict.get()` 复习（`current_user` 里那行）

```python
user = USERS.get(token)
#      └─┬─┘ └───┬───┘
#     查哪个   用什么查
```

| 写法 | 键存在 | 键不存在 |
|---|---|---|
| `USERS[token]` | 返回值 | **❌ KeyError → 500** |
| **`USERS.get(token)`** | 返回值 | **✅ None** |

**实测**：

```python
USERS["Bearer wrong"]        # ❌ KeyError: 'Bearer wrong'
USERS.get("Bearer wrong")    # ✅ None
USERS.get("Bearer wrong", "默认值")   # ✅ '默认值'
```

> **`.get()` = "查一下，没有就算了，别报错"。**
> **拿到 `None` 就说明"这个 token 我不认识"** → 后面 `raise 401`。

**你见过同一个写法**（Day 29 调度器）：

```python
n = attempts.get(task_id, 0) + 1      # 查不到就当 0
```

---

## 十一、真实项目里 `Depends` 的四个经典用途

| 用途 | 依赖函数大概长什么样 |
|---|---|
| **鉴权** | `verify_token()` / `current_user()` / `require_admin()` |
| **数据库连接** | `get_db()` —— 每请求一个连接，用完自动关（用 `yield`） |
| **分页/排序/过滤** | `pagination()` / `sorting()` —— 10 个列表接口共用一个 |
| **公共业务** | `get_current_org()`（多租户）、`check_quota()`（额度） |

**做 RAG 项目时，`current_user` 和 `get_db` 会天天用。**

---

## 十二、day39_depends 目录里的三个文件

| 文件 | 内容 | 启动 |
|---|---|---|
| **`app.py`** | 题1 鉴权（含 `/admin-copy` 对照版 + `/debug-*` 排错接口） | `uvicorn app:app` |
| **`pagination_app.py`** | 题2 分页（`/items` `/users` `/search`） | `uvicorn pagination_app:app` |
| **`auth_app.py`** | 题3 三层鉴权（`/me` `/admin/dashboard` `/public`） | `uvicorn auth_app:app` |

**⚠️ 启动命令不同** —— 因为文件名不同。

---

## 十三、还没搞懂的

1. `Depends` 里用 `yield` 是什么写法？（听说能自动清理资源）
2. 依赖函数的返回值能不能是类实例（而不是 dict）？
3. 一个依赖被多个接口用，它是**每个请求算一次**还是**缓存**？
4. `Depends(verify_admin, use_cache=False)` 是干什么的？
5. 依赖里能不能改请求对象（比如往 `request.state` 里塞东西）？
