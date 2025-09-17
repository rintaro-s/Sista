from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Field, create_engine, Session, select, ForeignKey
from typing import Optional, List
from datetime import datetime
import os
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Dict, Any
import requests
from ai_client import call_llm

# simple JWT settings (for demo)
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict):
    to_encode = data.copy()
    # no exp for simplicity
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    message: str
    reply: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

DATABASE_URL = os.environ.get("DATABASE_URL")

# Fallback to a local sqlite file if DATABASE_URL not provided. This makes local dev easier
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./sista_dev.db"

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

app = FastAPI(title="Sista Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    status: str = "pending"
    category: Optional[str] = None
    due_date: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # user_id is required: tasks belong to a user
    user_id: int = Field(foreign_key="user.id")


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/", tags=["health"])
def health():
    return {"message": "Sista FastAPI backend is running"}


def get_current_user_id(authorization: Optional[str] = Header(None)) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    # verify user exists
    with Session(engine) as session:
        user = session.get(User, uid)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
    return uid


@app.get("/tasks", response_model=List[Task])
def list_tasks(user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        tasks = session.exec(select(Task).where(Task.user_id == user_id).order_by(Task.created_at)).all()
        return tasks


@app.post("/tasks", response_model=Task)
def create_task(task: Task, user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        db_task = Task(
            title=task.title,
            status=task.status or "pending",
            category=task.category,
            due_date=task.due_date,
            user_id=user_id,
        )
        session.add(db_task)
        session.commit()
        session.refresh(db_task)
        return db_task


@app.put("/tasks/{task_id}", response_model=Task)
@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task: Task, user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        db_task = session.get(Task, task_id)
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")
        if db_task.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not allowed")
        db_task.title = task.title
        db_task.status = task.status
        db_task.category = task.category
        db_task.due_date = task.due_date
        session.add(db_task)
        session.commit()
        session.refresh(db_task)
        return db_task


@app.delete("/tasks/{task_id}")
@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        db_task = session.get(Task, task_id)
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")
        if db_task.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not allowed")
        session.delete(db_task)
        session.commit()
        return {"ok": True}


# --- Auth endpoints ---


class UserCreate(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChatRequest(BaseModel):
    user_id: Optional[int] = None
    text: str
    role_sheet: Optional[dict] = None
    over_hallucination: Optional[bool] = False
    history: Optional[list] = None
    compressed_memory: Optional[dict] = None


class AIDecomposeRequest(BaseModel):
    prompt: str


class AITodo(BaseModel):
    id: int
    title: str
    status: str = "pending"
    note: Optional[str] = None
    order: Optional[int] = None


@app.post("/auth/register", response_model=Token)
def register(user: UserCreate):
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == user.username)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already registered")
        hashed = get_password_hash(user.password)
        db_user = User(username=user.username, hashed_password=hashed)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        token = create_access_token({"sub": str(db_user.id)})
        return Token(access_token=token)


@app.post("/auth/login", response_model=Token)
def login(form: UserCreate):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == form.username)).first()
        if not user or not verify_password(form.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        token = create_access_token({"sub": str(user.id)})
        return Token(access_token=token)


@app.get("/chats", response_model=List[ChatMessage])
def list_chats(user_id: int = Depends(get_current_user_id)):
    with Session(engine) as session:
        msgs = session.exec(select(ChatMessage).where(ChatMessage.user_id == user_id).order_by(ChatMessage.created_at)).all()
        return msgs


def get_user_id_from_auth(authorization: Optional[str]) -> Optional[int]:
    # kept for backward compatibility in case some internal code calls it
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return int(payload.get("sub"))
        except JWTError:
            return None
    return None


@app.post("/chats", response_model=ChatMessage)
def create_chat(msg: BaseModel, user_id: int = Depends(get_current_user_id)):
    # msg is expected to have .message attribute
    text = getattr(msg, "message", "")
    # simple mock reply
    reply = "...あ、それ、今やっといたほうがよくない？"
    if "やる気" in text:
        reply = "やる気ないなら、Sistaがちょっと手伝うね…"
    with Session(engine) as session:
        chat = ChatMessage(user_id=user_id, message=text, reply=reply)
        session.add(chat)
        session.commit()
        session.refresh(chat)
        return chat


@app.post("/chat")
def proxy_chat(req: ChatRequest, authorization: Optional[str] = Header(None)):
    """
    Proxy endpoint for the LLM. If OPENAI_API_KEY is set, forward to OpenAI's Chat Completions API.
    Expected payload follows LLM_client.py: {user_id, text, role_sheet, over_hallucination, history, compressed_memory}
    Returns JSON with keys: response, debug_info (optional), compressed_memory (optional).
    """
    # get optional user id from authorization header early
    user_id = get_user_id_from_auth(authorization)

    # Delegate to centralized ai_client
    result = call_llm(
        text=req.text,
        history=req.history,
        role_sheet=req.role_sheet,
        user_id=user_id,
        over_hallucination=req.over_hallucination,
        compressed_memory=req.compressed_memory,
    )

    if 'error' in result:
        # choose an appropriate HTTP status
        raise HTTPException(status_code=502, detail=result['error'])

    assistant_text = result.get('response', '')
    debug_info = result.get('debug_info')

    # store in DB
    with Session(engine) as session:
        chat = ChatMessage(user_id=user_id or 0, message=req.text, reply=assistant_text)
        session.add(chat)
        session.commit()
        session.refresh(chat)

    return {"response": assistant_text, "debug_info": debug_info, "compressed_memory": result.get('compressed_memory'), "created_at": chat.created_at.isoformat()}


@app.post("/api/execute")
async def execute_step(req: dict):
    return {"result": f"『{req.get('task')}』の最初の一歩を実行しました！（妹が代行）"}


# --- AI decomposition endpoint (returns JSON-formatted ToDo list) ---
@app.post('/ai/todos')
def ai_todos(req: AIDecomposeRequest, authorization: Optional[str] = Header(None)):
    """
    Produce a JSON ToDo list for a given prompt. This is a simple, deterministic decomposition
    used by the Streamlit dashboard. Returns: {"todos": [AITodo, ...]}
    """
    prompt = (req.prompt or '').strip()
    if not prompt:
        return {"todos": []}

    # Try to delegate decomposition to the LLM using centralized call_llm
    user_id = get_user_id_from_auth(authorization)
    llm_result = call_llm(text=prompt, history=None, role_sheet=None, user_id=user_id)
    if 'error' in llm_result:
        # Fall back to local heuristics but surface error info
        # Keep behavior robust: return local decomposition plus debug
        local = []
        parts = [p.strip() for p in prompt.replace('、', ',').split(',') if p.strip()]
        if len(parts) > 1:
            for i, p in enumerate(parts):
                local.append({"id": i+1, "title": p, "status": "pending", "order": i+1})
            return {"todos": local, "debug": {"llm_error": llm_result.get('error')}}
        sentences = [s.strip() for s in prompt.replace('。', '.').split('.') if s.strip()]
        if len(sentences) > 1:
            for i, s in enumerate(sentences):
                local.append({"id": i+1, "title": s, "status": "pending", "order": i+1})
            return {"todos": local, "debug": {"llm_error": llm_result.get('error')}}
        words = prompt.split()
        if len(words) <= 3:
            local.append({"id": 1, "title": f"{prompt} を小さく試す", "status": "pending", "order": 1})
            return {"todos": local, "debug": {"llm_error": llm_result.get('error')}}
        for i, piece in enumerate([words[0], ' '.join(words[1:2] if len(words) > 1 else words[0:1]), '報告する']):
            local.append({"id": i+1, "title": piece if piece else f"Step {i+1}", "status": "pending", "order": i+1})
        return {"todos": local, "debug": {"llm_error": llm_result.get('error')}}

    # llm_result has 'response' -- try to parse it into a list of todo titles
    resp_text = llm_result.get('response') or ''
    todos: List[Dict[str, Any]] = []

    # If the model returned JSON array, try to parse
    import json
    parsed = None
    try:
        parsed = json.loads(resp_text)
    except Exception:
        parsed = None

    if isinstance(parsed, list):
        for i, item in enumerate(parsed):
            # accept either strings or dicts with 'title'
            if isinstance(item, str):
                title = item
            elif isinstance(item, dict):
                title = item.get('title') or item.get('task') or str(item)
            else:
                title = str(item)
            todos.append({"id": i+1, "title": title, "status": "pending", "order": i+1})
        return {"todos": todos, "debug": {"llm_raw": llm_result.get('debug_info')}}

    # Otherwise split by newlines/numbered lines or commas
    lines = [l.strip() for l in resp_text.replace('、', ',').replace('\r', '').split('\n') if l.strip()]
    if not lines:
        lines = [p.strip() for p in resp_text.replace('、', ',').split(',') if p.strip()]

    if lines:
        # remove leading numbering like '1.' or '①'
        import re
        cleaned = []
        for l in lines:
            m = re.sub(r'^\s*[0-9０-９]+[\).．:：\s]+', '', l)
            m = re.sub(r'^\s*[①-⑨]\s*', '', m)
            cleaned.append(m.strip())
        for i, c in enumerate(cleaned):
            todos.append({"id": i+1, "title": c, "status": "pending", "order": i+1})
        return {"todos": todos, "debug": {"llm_raw": llm_result.get('debug_info')}}

    # Last resort: simple heuristic
    parts = [p.strip() for p in prompt.replace('、', ',').split(',') if p.strip()]
    for i, p in enumerate(parts):
        todos.append({"id": i+1, "title": p, "status": "pending", "order": i+1})
    return {"todos": todos, "debug": {"llm_raw": llm_result.get('debug_info')}}
