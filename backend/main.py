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
import requests

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

    # First: if LMStudio local LLM is configured, forward there
    LMSTUDIO_URL = os.environ.get('LMSTUDIO_URL')
    if LMSTUDIO_URL:
        # Prepare a generic payload for LMStudio/local LLMs. Many local LLM frontends accept {input} or {prompt}.
        # Only include user_id if it is an integer; some LLM frontends expect numeric user ids
        lm_payload = {
            "input": req.text,
            "history": req.history,
            "role_sheet": req.role_sheet,
            "over_hallucination": req.over_hallucination,
            "compressed_memory": req.compressed_memory,
        }
        # attempt to coerce user_id to int; if not possible, omit it to avoid 422 from LM server
        try:
            if user_id is not None:
                lm_payload_user_id = int(user_id)
                lm_payload["user_id"] = lm_payload_user_id
        except Exception:
            # skip setting user_id if it cannot be parsed as int
            pass
        try:
            r = requests.post(LMSTUDIO_URL, json=lm_payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            # Try several common keys for response text
            assistant_text = ''
            if isinstance(data, dict):
                for k in ('response', 'text', 'output', 'result'):
                    if k in data and data[k]:
                        assistant_text = data[k]
                        break
                # some servers embed in results list
                if not assistant_text and 'results' in data and isinstance(data['results'], list) and data['results']:
                    first = data['results'][0]
                    if isinstance(first, dict):
                        assistant_text = first.get('content') or first.get('text') or str(first)
                    else:
                        assistant_text = str(first)

            # store in DB
            with Session(engine) as session:
                chat = ChatMessage(user_id=user_id or 0, message=req.text, reply=assistant_text)
                session.add(chat)
                session.commit()
                session.refresh(chat)

            return {"response": assistant_text, "debug_info": {"lm_raw": data}, "compressed_memory": None, "created_at": chat.created_at.isoformat()}
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=502, detail=f"LMStudio request failed: {e}")

    # Next fallback: OpenAI if configured
    OPENAI_KEY = os.environ.get('OPENAI_API_KEY')
    if not OPENAI_KEY:
        raise HTTPException(status_code=501, detail='No LLM configured. Set LMSTUDIO_URL or OPENAI_API_KEY on the server.')

    model = os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo')
    # user_id already retrieved above
    # build messages list: include system prompt from role_sheet if provided
    messages = []
    if req.role_sheet and isinstance(req.role_sheet, dict):
        tone = req.role_sheet.get('tone')
        if tone:
            messages.append({"role": "system", "content": f"You are an assistant. Tone: {tone}"})

    # include history if provided
    if req.history and isinstance(req.history, list):
        for h in req.history:
            role = h.get('role') if isinstance(h, dict) else 'user'
            content = h.get('content') if isinstance(h, dict) else str(h)
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": req.text})

    openai_url = 'https://api.openai.com/v1/chat/completions'
    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(os.environ.get('OPENAI_TEMPERATURE', '0.7')),
    }

    headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
    try:
        r = requests.post(openai_url, json=payload, headers=headers, timeout=20)
        r.raise_for_status()
        data = r.json()
        # extract assistant content (first choice)
        assistant_text = ''
        try:
            assistant_text = data.get('choices', [])[0].get('message', {}).get('content', '')
        except Exception:
            assistant_text = data.get('choices', [0])

        debug_info = {"openai": {k: data.get(k) for k in ('usage',)}}

        # store in DB
        with Session(engine) as session:
            chat = ChatMessage(user_id=user_id or 0, message=req.text, reply=assistant_text)
            session.add(chat)
            session.commit()
            session.refresh(chat)

        return {"response": assistant_text, "debug_info": debug_info, "compressed_memory": None, "created_at": chat.created_at.isoformat()}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {e}")


@app.post("/api/execute")
async def execute_step(req: dict):
    return {"result": f"『{req.get('task')}』の最初の一歩を実行しました！（妹が代行）"}
