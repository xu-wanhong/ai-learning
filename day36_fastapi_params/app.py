"""Day 36 · FastAPI 收参数：查询参数 / 请求体 / 嵌套模型 / 校验 / HTTPException

跑法：
    cd ~/dev/ai-learning/day36_fastapi_params
    ../.venv/bin/python -m uvicorn app:app --reload
测试：
    curl "http://127.0.0.1:8000/articles?author=tom"
    （URL 里有 ? 和 & 时，终端里【必须加引号】—— zsh 会把 ? 当通配符）
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Day 36 · 参数练习")


# ==================== 题 1 · 查询参数 ====================
@app.get("/articles")
def list_articles(author: str, page: int = 1, size: int = 10):
    return {"author": author, "page": page, "size": size}


# ==================== 题 2 · 请求体 + Pydantic ====================
class SummarizeRequest(BaseModel):
    text: str
    max_words: int = 100


@app.post("/summarize")
def summarize(req: SummarizeRequest):
    return {
        "原文长度": len(req.text),
        "上限": req.max_words,
        "预览": req.text[:20],
    }


# ==================== 题 3 · 嵌套模型 ====================
class Message(BaseModel):
    role: str = "user"
    content: str


class ChatRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: list[Message]


@app.post("/chat")
def chat(req: ChatRequest):
    if not req.messages:                       # 空数组：优雅处理，别让 [-1] 崩成 500
        return {"模型": req.model, "消息数": 0, "最后一条": None, "最后角色": None}
    last = req.messages[-1]
    return {
        "模型": req.model,
        "消息数": len(req.messages),
        "最后一条": last.content,
        "最后角色": last.role,
    }


# ==================== 题 4 · Field 校验 ====================
class SignupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=20, description="3~20 个字")
    age: int = Field(ge=18, le=120, description="18~120 岁")
    email: str = Field(pattern=r".*@.*", description="必须包含 @")


@app.post("/signup")
def signup(req: SignupRequest):
    return {"注册成功": req}


# ==================== 题 5 · HTTPException ====================
ARTICLES = {1: "第一篇文章", 2: "第二篇文章", 3: "第三篇文章"}


@app.get("/articles/{article_id}")
def get_article(article_id: int):
    if article_id < 0:
        raise HTTPException(status_code=400, detail=f"id 不能是负数：{article_id}")
    if article_id not in ARTICLES:
        raise HTTPException(status_code=404, detail=f"文章 {article_id} 不存在")
    return {"id": article_id, "title": ARTICLES[article_id]}
