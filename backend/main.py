
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# CORS設定（フロントと連携用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StepRequest(BaseModel):
    task: str

class StepResponse(BaseModel):
    steps: List[str]
    message: str

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

# 最初の一歩提案API
@app.post("/api/step", response_model=StepResponse)
async def propose_step(req: StepRequest):
    # モック: タスクに応じて最初の一歩を返す
    if "税金" in req.task:
        steps = ["国税庁のHPを開く", "必要な書類を確認する"]
        msg = "まず国税庁のHPを開いて。開いた？開いてない？じゃあリンク送るね。"
    else:
        steps = ["Googleで調べる", "TODOリストに追加する"]
        msg = "まずは調べてみようか？"
    return StepResponse(steps=steps, message=msg)

# 最初の一歩実行API
@app.post("/api/execute")
async def execute_step(req: StepRequest):
    # モック: 実行結果を返す
    return {"result": f"『{req.task}』の最初の一歩を実行しました！（妹が代行）"}

# チャットAPI
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # モック: Sista風の返答
    reply = "…あ、それ、今やっといたほうがよくない？"
    if "やる気" in req.message:
        reply = "やる気ないなら、Sistaがちょっと手伝うね…"
    elif "ありがとう" in req.message:
        reply = "ふふん、感謝してもいいよ？"
    return ChatResponse(reply=reply)

# 動作確認用
@app.get("/")
def read_root():
    return {"message": "Sista FastAPI backend is running!"}
