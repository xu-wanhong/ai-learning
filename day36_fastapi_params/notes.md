# Day 36 · FastAPI 收参数

2026-11-10 · macOS · FastAPI 0.162.0

> **Day 35 只会收"路径里一个变量"。今天学会收三种参数 —— 接口才真的能用。**

---

## 一、⭐ 三种参数怎么选

| 类型 | 长什么样 | 放哪 | 适合 | 代码 |
|---|---|---|---|---|
| **路径参数** | `/items/5` | **URL 的一部分** | **定位"哪一个"** | `def f(item_id: int)` |
| **查询参数** | `/search?q=x&limit=5` | **`?` 后面** | **筛选、选项（可省略）** | `def f(q: str, limit: int = 10)` |
| **请求体** | POST 的 JSON | **body 里** | **提交一大坨数据** | `def f(req: MyModel)` |

**判断口诀**：

```
"我要哪一个"     → 路径参数   /items/5
"我要怎么筛"     → 查询参数   ?q=python&limit=5
"我要提交什么"   → 请求体     {"messages": [...]}
```

**⭐ FastAPI 靠「参数类型」自动判断去哪读**：

| 参数写成 | 去哪读 |
|---|---|
| `str` / `int` / `float` | **查询参数** |
| **`BaseModel` 的子类** | **请求体** |
| URL 里有 `{同名}` | **路径参数** |

---

## 二、查询参数

```python
@app.get("/articles")
def list_articles(author: str, page: int = 1, size: int = 10):
    return {"author": author, "page": page, "size": size}
```

### 规则：有默认值 = 可选，没默认值 = 必填

| 写法 | 含义 |
|---|---|
| `author: str` | **必填**（不给 → 422） |
| `page: int = 1` | **可选**（不给 → 1） |

**实测**：

```bash
$ curl "http://127.0.0.1:8000/articles?author=tom"
{"author":"tom","page":1,"size":10}

$ curl "http://127.0.0.1:8000/articles?author=tom&page=3&size=20"
{"author":"tom","page":3,"size":20}

$ curl "http://127.0.0.1:8000/articles"
422  missing: author

$ curl "http://127.0.0.1:8000/articles?author=tom&page=abc"
422  int_parsing: page
```

> **`page: int` 里的 `int` 不是装饰** —— 自动把 URL 里的字符串 `"3"` 转成数字 `3`，传 `"abc"` 自动报 422。

---

## 三、请求体 + Pydantic

### 三步

```python
# ① 定义"请求长什么样"
class SummarizeRequest(BaseModel):
    text: str
    max_words: int = 100

# ② 接口参数写成这个类型
@app.post("/summarize")
def summarize(req: SummarizeRequest):

# ③ 用 req.xxx 取字段
    return {"原文长度": len(req.text), "上限": req.max_words, "预览": req.text[:20]}
```

### `POST` 而不是 `GET`

| 方法 | 参数放哪 |
|---|---|
| `get` | URL 里 |
| **`post`** | **body 里**（适合传长文本、复杂结构） |

**`HTTP body` 里有很多东西 → 必须 POST。**

### 切片 `[:20]`

```python
req.text[:20]        # 前 20 个字符，不够 20 就全给（【不报错】）
req.text[20]         # ❌ 第 21 个字符，越界会 IndexError
```

> **有冒号 = 切片（安全）；没冒号 = 索引（会越界）。**

### 实测

```bash
$ curl -X POST -H "Content-Type: application/json" \
    -d '{"text":"这是一段很长的文章内容"}' http://127.0.0.1:8000/summarize
{"原文长度":11,"上限":100,"预览":"这是一段很长的文章内容"}
```

**`max_words` 没给 → 默认 100。**

---

## 四、⭐ 嵌套模型

```python
class Message(BaseModel):
    role: str = "user"
    content: str


class ChatRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: list[Message]        # ← 一个数组，每个元素是 Message
```

### JSON 和模型的对应关系

**发的 JSON**：

```json
{
  "model": "gpt-4o",
  "messages": [
    {"role": "system", "content": "你是助手"},
    {"content": "你好"}
  ]
}
```

**解析成**：

```
ChatRequest
 ├── model    = "gpt-4o"
 └── messages = [ Message(role="system", content="你是助手"),
                Message(role="user",   content="你好") ]   ← 没给 role，用默认值
```

**实测（把类型打出来）**：

```
req 本身是什么类型        <class 'app.ChatRequest'>
req.messages 是什么类型   <class 'list'>
第 0 个是什么类型         <class 'app.Message'>      ← 是对象，不是 dict！
第 0 个的 role            system
```

> **⭐ `messages` 里的元素已经变成 `Message` 对象** —— 所以能用 `.content` 访问。

### 用数据

```python
@app.post("/chat")
def chat(req: ChatRequest):
    if not req.messages:                       # ① 先判空
        return {"消息数": 0, "最后一条": None, "最后角色": None}

    last = req.messages[-1]                    # ② 取最后一条（-1 = 倒数第一）
    return {
        "消息数": len(req.messages),
        "最后一条": last.content,               # ③ 对象字段用 .
        "最后角色": last.role,
    }
```

### ⚠️ 判空是必须的

```python
req.messages[-1]     # 如果是 [] → IndexError → FastAPI 返回 500
```

**`if not req.messages:`** 就是判空（空列表是"假"）。

**500 vs 422**：**500 = 你的代码崩了（难看）；422 = 客户端传错（正常）。**

### 嵌套模型自动逐元素校验

```bash
# content 传数字
$ -d '{"messages":[{"role":"user","content":123}]}'
{"detail":[{"type":"string_type",
  "loc":["body","messages",0,"content"],       ← 精确到"第 0 个的 content"
  "msg":"Input should be a valid string","input":123}]}

# 数组里塞字符串
$ -d '{"messages":["hello"]}'
{"detail":[{"type":"model_attributes_type",
  "loc":["body","messages",0],
  "msg":"Input should be a valid dictionary or object to extract fields from"}]}

# messages 传对象（不是数组）
$ -d '{"messages":{"content":"hi"}}'
{"detail":[{"type":"list_type","loc":["body","messages"],
  "msg":"Input should be a valid list"}]}
```

---

## 五、⭐ 422 的响应体怎么读

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "username"],
      "msg": "String should have at least 3 characters",
      "input": "to",
      "ctx": {"min_length": 3}
    }
  ]
}
```

| 字段 | 意思 |
|---|---|
| `type` | **错误类型**（机器读）`string_too_short` / `less_than_equal` / `int_parsing` / `missing` |
| **`loc`** | **错在哪**（坐标） |
| `msg` | 人话描述 |
| `input` | 你传进去的值 |
| `ctx` | 约束条件 |

### `loc` 是坐标

| `loc` | 意思 |
|---|---|
| `["query", "page"]` | **查询参数**里的 `page` |
| `["path", "item_id"]` | **路径参数**里的 `item_id` |
| `["body", "username"]` | **请求体**里的 `username` |
| **`["body", "messages", 0, "content"]`** | **请求体 → messages → 第 0 个 → content** |

> **看到 `0` 就是"数组里的第几个"** —— 嵌套模型也能精确定位。

---

## 六、Field 校验

```python
from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=20, description="3~20 个字")
    age: int = Field(ge=18, le=120, description="18~120 岁")
    email: str = Field(pattern=r".*@.*", description="必须包含 @")
```

| 参数 | 意思 | 用于 |
|---|---|---|
| `min_length` / `max_length` | 长度 | `str` |
| **`ge`** | **≥**（greater or equal） | 数字 |
| **`le`** | **≤**（less or equal） | 数字 |
| `gt` / `lt` | > / < | 数字 |
| **`pattern`** | 正则匹配 | `str` |
| **`description`** | **说明 → 显示在 `/docs` 里** ⭐ | 任意 |

**实测 5 条**：

```
① {"username":"tom","age":25,"email":"a@b.com"}  → 200 ✅
② username 2 个字                                → 422 string_too_short (min_length 3)
③ age=10                                         → 422 greater_than_equal (ge 18)
④ age=200                                        → 422 less_than_equal (le 120)
⑤ email 没 @                                     → 422 string_pattern_mismatch
```

> **`pattern=r".*@.*"` 里的 `r` 别省** —— 原始字符串，`\` 不会被转义。
> **写正则一律加 `r`**（`r"\d+"`、`r"^https?://"`）。

---

## 七、主动报错：`HTTPException`

**上面所有错误都是"FastAPI 自动发现的"。但业务判断要你自己报。**

```python
from fastapi import HTTPException


@app.get("/articles/{article_id}")
def get_article(article_id: int):
    if article_id < 0:
        raise HTTPException(status_code=400, detail=f"id 不能是负数：{article_id}")
    if article_id not in ARTICLES:
        raise HTTPException(status_code=404, detail=f"文章 {article_id} 不存在")
    return {"id": article_id, "title": ARTICLES[article_id]}
```

**实测**：

```
/articles/1   → [200] {"id":1,"title":"第一篇文章"}
/articles/4   → [404] {"detail":"文章 4 不存在"}
/articles/-1  → [400] {"detail":"id 不能是负数：-1"}
```

**`raise HTTPException(...)` 会自动变成 `{"detail": "..."}`** —— 不用自己构造响应。

### 常用状态码

| 码 | 意思 | 谁报 |
|---|---|---|
| **200** | 成功 | 默认 |
| 201 | 创建成功 | 你（POST 新建） |
| **400** | 请求逻辑有问题 | **你** |
| 401 | 没认证 | 你 |
| 403 | 没权限 | 你 |
| **404** | 找不到 | **你** |
| **422** | 校验失败 | **FastAPI 自动** |
| 500 | 服务器崩了 | **你代码有 bug** |

---

## 八、踩的坑

### ⚠️ 1. 404 的三种原因（**我今天全撞了一遍**）

```bash
$ curl .../articles?author=tom
{"detail":"Not Found"}
```

**`Not Found` 是 FastAPI 说"这个路径我没注册过"。**

| # | 原因 | 怎么查 |
|---|---|---|
| **1** | **路径写错**（`/author/page/size` vs `/articles`） | `curl .../openapi.json` 看实际路由 |
| **2** | **旧 uvicorn 还在跑**（改了代码没重启） | 加 `--reload` |
| **3** | **8000 上是另一个 app** | `lsof -i :8000` |

**诊断三步**：

```bash
lsof -i :8000 -P -n
curl -s http://127.0.0.1:8000/openapi.json | python3 -c "
import json,sys; d=json.load(sys.stdin); [print(p) for p in d['paths']]"
grep -n "app.get\|app.post" app.py
```

### ⚠️ 2. ⭐ **zsh 会把 `?` 当通配符** —— 终端里 URL 必须加引号

```bash
$ curl http://127.0.0.1:8000/articles?author=tom
zsh: no matches found: http://127.0.0.1:8000/articles?author=tom
```

**命令根本没执行。**

**原因**：**zsh 里 `?` 是"匹配任意一个字符"的通配符**（和 `*` 一样）：

```
$ ls a?b.txt       → a1b.txt a2b.txt      （匹配到了，正常）
$ echo size?author → zsh: no matches found  （没文件匹配 → 直接报错）
```

> **bash 匹配不到时会把原样字符串传下去（能跑）；zsh 直接报错（跑不了）。**
> **macOS 默认是 zsh，所以撞上了。**

**修法**：

```bash
curl "http://127.0.0.1:8000/articles?author=tom"
```

> **规矩：URL 里有 `?` `&` `#` `*` 时，一律加引号。**
> **不加引号的话，`&` 还会把命令切成两条放到后台。**

### ⚠️ 3. 装饰器后面必须跟函数

```python
@app.post("/")          # ❌ 后面什么都没有 → SyntaxError: invalid syntax
```

**装饰器是"贴在函数上的"** —— 没有函数，语法不完整。

### ⚠️ 4. POST JSON 必须带 `Content-Type`

```bash
curl -X POST -d '{"text":"hi"}' URL                              # ❌ 422
curl -X POST -H "Content-Type: application/json" -d '{"text":"hi"}' URL   # ✅
```

**不加的话，curl 默认发 `application/x-www-form-urlencoded`** —— 不是 JSON。

### ⚠️ 5. 空数组上取 `[-1]` → 500

```python
req.messages[-1]      # 如果 messages 是 [] → IndexError → 500
```

**先判空**：`if not req.messages:`

---

## 九、命令速查

```bash
# 启动
cd ~/dev/ai-learning/day36_fastapi_params
uvicorn app:app --reload

# 看有哪些接口
curl -s http://127.0.0.1:8000/openapi.json | python3 -c "
import json,sys; d=json.load(sys.stdin); [print(p) for p in d['paths']]"

# 测查询参数（⭐ 加引号）
curl "http://127.0.0.1:8000/articles?author=tom&page=3"

# 测 POST
curl -X POST -H "Content-Type: application/json" -d '{"text":"hi"}' \
  http://127.0.0.1:8000/summarize

# 只看状态码
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000/articles?author=tom"
```

---

## 十、还没搞懂的

1. `Field(pattern=...)` 用的是哪种正则？（Python `re` 语法？）
2. 请求体里的字段名能不能用中文？（如果能，会有什么问题）
3. 校验失败时，怎么把 422 的**默认英文错误**改成中文？
4. 一个接口能不能**同时**收路径参数 + 查询参数 + 请求体？
5. `BaseModel` 和 `dataclass` 有什么区别，为什么 FastAPI 用前者？
