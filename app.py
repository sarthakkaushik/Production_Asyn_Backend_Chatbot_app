from contextlib import asynccontextmanager
from typing import Optional
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Boolean, Column, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from pydantic import BaseModel
from chatbot_workflow import ChatbotWorkflow

# Database configuration
DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/chatbot_db"
engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

chatbot_workflow = ChatbotWorkflow()

class Thread(Base):
    __tablename__ = "threads"
    thread_id = Column(String, primary_key=True, index=True)
    messages = Column(Text, nullable=True)  # Store messages as JSON string
    error = Column(Boolean, default=False)

def initialize_database():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ThreadResponse(BaseModel):
    thread_id: str
    messages: Optional[list] = None
    error: bool

class StartThreadResponse(BaseModel):
    thread_id: str

class ChatRequest(BaseModel):
    message: str

@app.post("/start_thread", response_model=StartThreadResponse)
async def start_thread(db: Session = Depends(get_db)):
    thread_id = str(uuid4())
    new_thread = Thread(thread_id=thread_id, error=False)
    db.add(new_thread)
    db.commit()
    db.refresh(new_thread)
    return StartThreadResponse(thread_id=new_thread.thread_id)

@app.post("/chat/{thread_id}", response_model=ThreadResponse)
async def chat(thread_id: str, request: ChatRequest, db: Session = Depends(get_db)):
    thread = db.query(Thread).filter(Thread.thread_id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread ID does not exist.")
    
    try:
        response_state = await chatbot_workflow.ainvoke(
            input={"message": request.message},
            config={"thread_id": thread_id}
        )
        
        thread.messages = response_state.get("messages")
        thread.error = response_state.get("error", False)
        db.commit()
        
        return ThreadResponse(
            thread_id=thread.thread_id,
            messages=thread.messages,
            error=thread.error
        )
    except Exception as e:
        thread.error = True
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))