from fastapi import FastAPI
from fastapi.responses import JSONResponse



class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


app = FastAPI(default_response_class=UTF8JSONResponse)

@app.get("/")
def root():
    return {"status":"ok" , "msg":"服务活着"}

@app.get("/hello/{name}")
def holle(name: str):
    return {"msg":f"我是{name}"}

@app.get("/user/{name}")
def user(name:str):
    return {"name":"f{naem}","长度":len(name)}

@app.get("/calc/{a}/{b}")
def calc(a:float,b:float):
    return a+b