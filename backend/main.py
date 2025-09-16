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

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@db:5432/sista"
)

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
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/", tags=["health"])
def health():
    return {"message": "Sista FastAPI backend is running"}


@app.get("/tasks", response_model=List[Task])
def list_tasks(authorization: Optional[str] = Header(None)):
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = int(payload.get("sub"))
        except JWTError:
            user_id = None

    with Session(engine) as session:
        if user_id:
            tasks = session.exec(select(Task).where(Task.user_id == user_id).order_by(Task.created_at)).all()
        else:
            tasks = session.exec(select(Task).order_by(Task.created_at)).all()
        return tasks


@app.post("/tasks", response_model=Task)
def create_task(task: Task, authorization: Optional[str] = Header(None)):
    # Expect Authorization header via FastAPI dependency
    from fastapi import Request
    request: Request = Request.scope.get("request") if hasattr(Request, "scope") else None
    # Instead use header approach: read Authorization from environ header if provided by middleware
    # For clarity, accept user_id provided in task.user_id or fall back to None
    user_id = get_user_id_from_auth(authorization) or task.user_id
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
def update_task(task_id: int, task: Task, authorization: Optional[str] = Header(None)):
    # Require ownership: task.user_id must match existing owner (or be None)
    with Session(engine) as session:
        db_task = session.get(Task, task_id)
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")
            # enforce ownership via authorization header
            caller_id = get_user_id_from_auth(authorization)
            if caller_id and db_task.user_id and caller_id != db_task.user_id:
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
def delete_task(task_id: int, authorization: Optional[str] = Header(None)):
    with Session(engine) as session:
        db_task = session.get(Task, task_id)
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")
        caller_id = get_user_id_from_auth(authorization)
        if caller_id and db_task.user_id and caller_id != db_task.user_id:
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
def list_chats(authorization: Optional[str] = Header(None)):
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = int(payload.get("sub"))
        except JWTError:
            user_id = None

    with Session(engine) as session:
        if user_id:
            msgs = session.exec(select(ChatMessage).where(ChatMessage.user_id == user_id).order_by(ChatMessage.created_at)).all()
        else:
            msgs = session.exec(select(ChatMessage).order_by(ChatMessage.created_at)).all()
        return msgs


def get_user_id_from_auth(authorization: Optional[str]) -> Optional[int]:
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return int(payload.get("sub"))
        except JWTError:
            return None
    return None


@app.post("/chats", response_model=ChatMessage)
def create_chat(msg: BaseModel, authorization: Optional[str] = Header(None)):
    # msg is expected to have .message attribute
    user_id = get_user_id_from_auth(authorization)
    text = getattr(msg, "message", "")
    # simple mock reply
    reply = "...あ、それ、今やっといたほうがよくない？"
    if "やる気" in text:
        reply = "やる気ないなら、Sistaがちょっと手伝うね…"
    with Session(engine) as session:
        chat = ChatMessage(user_id=user_id or 0, message=text, reply=reply)
        session.add(chat)
        session.commit()
        session.refresh(chat)
        return chat


@app.post("/api/execute")
async def execute_step(req: dict):
    return {"result": f"『{req.get('task')}』の最初の一歩を実行しました！（妹が代行）"}


@app.get("/", tags=["health"])
def read_root():
    return {"message": "Sista FastAPI backend is running!"}
