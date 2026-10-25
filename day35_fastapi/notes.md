# Day 35 · FastAPI 第一个接口

2026-10-25 · macOS · FastAPI 0.162.0 / uvicorn 0.54.0

> **目标：有个能被 `curl` 调通的 API。**
> 今天只学四个东西：**写接口 / 跑起来 / 看文档 / 路径参数**。

---

## 一、最小程序

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "msg": "服务活着"}
```

| 行 | 意思 |
|---|---|
| `from fastapi import FastAPI` | 引入框架 |
| `app = FastAPI()` | **创建应用**（后面都挂在这个 `app` 上） |
| **`@app.get("/")`** | **注册路由**：有人 `GET /` 时，调用下面那个函数 |
| `def root():` | 处理函数（**普通 `def` 就行，不必须是 `async`**） |
| `return {...}` | **返回 dict → FastAPI 自动转成 JSON** |

### `@app.get("/")` 是什么

```python
@app.get("/")          # ← 装饰器：把这个 URL 挂到下面的函数上
def root():
    return {"status": "ok"}
```

**读法**：**"当有人 `GET /`，执行下面这个函数，把返回值当 JSON 发回去。"**

**HTTP 方法最常用两个**：

| 方法 | 什么时候用 |
|---|---|
| **`GET`** | 拿数据（查） |
| **`POST`** | 提交数据（创建 / 让 AI 干活） |

---

## 二、跑起来

```bash
uvicorn app:app --reload
```

```bash
uvicorn  app:app  --reload
         └──┬───┘  └──┬──┘
            │         └── 改了代码自动重启（开发时用）
            └── app.py 文件里的 app 变量
```

**看到这几行才算起来**：

```
INFO:     Started server process [43761]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

**`Ctrl+C` 停掉。**

> **⚠️ `--reload` 只用于开发**。生产（服务器上）不要加 —— 它会监视文件变化，白费 CPU。

### 用后台方式跑（Day 34 学的）

```bash
nohup ~/dev/ai-learning/.venv/bin/python -m uvicorn app:app --port 8000 > app.log 2>&1 &
```

> **⚠️ `python` 前面必须是 venv 的完整路径。**
> 只写 `python` / `python3` 会用系统的 Python —— **它没装 fastapi**，直接报 `ModuleNotFoundError`。

**为什么加 `-m uvicorn`**：
`uvicorn` 这个可执行文件在 `.venv/bin/` 里，但直接调 venv 的 python 时要用 `-m` 让它"当模块跑"。

**两种写法都对**：

```bash
uvicorn app:app --port 8000                                 # 直接用 venv 里的 uvicorn
~/dev/ai-learning/.venv/bin/python -m uvicorn app:app ...   # 用 venv 的 python 跑模块（推荐）
```

---

## 三、⭐ `/docs` —— FastAPI 最大的卖点

**浏览器打开**：`http://127.0.0.1:8000/docs`

**能看到所有接口，还能直接点 "Try it out" 发请求。**

| 地址 | 是什么 |
|---|---|
| **`/docs`** | **Swagger UI**（能点、能测）← 最常用 |
| `/redoc` | 另一种文档样式（只能看） |
| `/openapi.json` | 接口的 JSON 描述（**给机器看的**） |

**实测 `/openapi.json` 能列出所有接口**：

```
GET   /
GET   /hello/{name}
GET   /user/{name}
GET   /calc/{a}/{b}
```

> **你一行文档都没写，文档自动就有了。**
> **改了参数类型，文档自动跟着变。这是 FastAPI 相对 Flask 最大的优势。**

---

## 四、路径参数

```python
@app.get("/items/{item_id}")
def get_item(item_id: int):
    return {"item_id": item_id}
```

**`{item_id}`** 是**占位符**，**函数参数名必须和它一样**。

### 类型标注会做什么（**这是 FastAPI 的核心**）

```python
def get_item(item_id: int):
```

**那个 `: int` 不是装饰** —— FastAPI 会：

| 自动做的事 | 实测结果 |
|---|---|
| **把 URL 里的字符串 `"5"` 转成数字 `5`** | `{"item_id":5}`（类型是 `int`） |
| **传错类型自动报 422** | `GET /items/abc` → `422` |
| **自动写进 `/docs`** | 文档里标成 `integer` |

**422 的响应体**：

```json
{"detail":[{"type":"int_parsing","loc":["path","item_id"],
  "msg":"Input should be a valid integer, unable to parse string as an integer",
  "input":"abc"}]}
```

> **这个错误是 FastAPI 自动产生的，你一行校验代码都没写。**

### 多个路径参数

```python
@app.get("/calc/{a}/{b}")
def calc(a: int, b: int):
    return {"结果": a + b}
```

```bash
$ curl http://127.0.0.1:8000/calc/3/5
{"结果":8}
```

---

## 五、今天踩的坑

### ⚠️ 1. 浏览器里中文乱码 → `Content-Type` 缺 `charset=utf-8`

**现象**：`curl` 显示正常，**浏览器里显示 `æå¡æ´»ç`**。

**原因**：FastAPI 默认发的 header 是：

```
content-type: application/json          ← 没有 charset
```

**字节本身是对的 UTF-8**（`e69c8d` = 服），**但浏览器看不到编码声明，可能按本地默认编码去解**。

**修法**（3 行，全局生效）：

```python
from fastapi.responses import JSONResponse


class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


app = FastAPI(default_response_class=UTF8JSONResponse)
```

**改完的 header**：

```
content-type: application/json; charset=utf-8
```

**怎么判断是不是这个原因**：

```bash
curl -s -i http://127.0.0.1:8000/ | grep -i content-type
```

| 看到 | 结论 |
|---|---|
| `application/json`（没 charset） | ✅ 就是这个原因 |
| `application/json; charset=utf-8` | 不是这个原因，另找 |

**几种乱码长什么样**：

| 你看到 | 原因 |
|---|---|
| `æå¡æ´»ç` | 被当 **Latin-1** 解码 |
| `鏈嶅姟娲荤潃` | 被当 **GBK** 解码 |
| `�����` | 编码根本对不上 |
| 方框 `□□□` | **字体问题**，不是编码 |

---

### ⚠️ 2. 字符串少了 `f` 前缀

```python
return {"name": "f{naem}", "长度": len(name)}     # ❌ 打印出字面的 f{naem}
return {"name": name, "长度": len(name)}          # ✅
```

**`"f{...}"` 没有 `f` 前缀 = 普通字符串**，`{}` 不会被替换。

**顺便**：`naem` 是 `name` 的拼写错误 —— 但**因为没写 `f`，它不报错**，只是打印出字面的 `f{naem}`。

> **这就是"不报错但结果错"那一族** —— 和之前 `f"结束(name)"`、`"开始{name}"` 是**同一类**。

---

### ⚠️ 3. 返回裸值 vs 返回 dict

```python
@app.get("/calc/{a}/{b}")
def calc(a: float, b: float):
    return a + b                    # ❌ 响应体就是 "8.0"
```

**两种问题**：

| 问题 | 后果 |
|---|---|
| **返回裸数字** | 响应体是 `8.0`，不是 `{"结果": 8}` |
| **用了 `float`** | `3 + 5` → `8.0`（带小数点） |

**正确**：

```python
@app.get("/calc/{a}/{b}")
def calc(a: int, b: int):
    return {"结果": a + b}          # → {"结果": 8}
```

> **约定**：**接口一律返回 `dict`（或 Pydantic 模型）**。
> 裸值能用，但**以后想加字段（比如加个状态）就得改客户端**。

---

### ⚠️ 4. `--reload` 只用于开发

```bash
uvicorn app:app --reload          # ✅ 本地开发
uvicorn app:app --host 0.0.0.0    # ✅ 部署（不加 --reload）
```

---

### ⚠️ 5. `nohup` 里 `python` 要写完整路径

```bash
nohup python3 -m uvicorn app:app ...                      # ❌ 系统 python，没装 fastapi
nohup ~/dev/ai-learning/.venv/bin/python -m uvicorn ...   # ✅
```

---

## 六、命令速查

```bash
# 启动（开发）
uvicorn app:app --reload

# 启动（后台）
nohup ~/dev/ai-learning/.venv/bin/python -m uvicorn app:app --port 8000 > app.log 2>&1 &

# 测
curl http://127.0.0.1:8000/
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/
curl -s -i http://127.0.0.1:8000/ | head -8          # 看 header
curl -s http://127.0.0.1:8000/openapi.json | python3 -m json.tool  # 看接口列表

# 看日志
tail -f app.log

# 停
kill $(lsof -ti :8000)
```

---

## 七、还没搞懂的

1. `def` 和 `async def` 都能定义接口，什么时候必须用 `async`？
2. 返回裸值 `8.0` 和返回 `{"结果": 8}`，除了好看，还有什么实际区别？
3. `/docs` 页面是怎么"知道"参数类型的？（提示：去看 `/openapi.json`）
4. `422` 和 `400` 都是"客户端错误"，为什么 FastAPI 用 422？
