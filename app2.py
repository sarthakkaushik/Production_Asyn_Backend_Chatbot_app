import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, String, Boolean, Text, create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from uuid import uuid4
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from asyncio import WindowsSelectorEventLoopPolicy
import asyncio

# Set the event loop policy before any async operations
asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())



from Chatbotflow import Chatbotflow



load_dotenv()

DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:admin@localhost:5432/postgres"
TARGET_DATABASE_URL = "postgresql+psycopg://postgres:admin@localhost:5432/threads_db"

default_engine = create_engine(DEFAULT_DATABASE_URL, future=True)
target_engine = create_engine(TARGET_DATABASE_URL, future=True)

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine)

human_workflow= Chatbotflow()

class Thread(Base):
    __tablename__ = "threads"
    thread_id = Column(String, primary_key=True, index=True)
    # question_asked = Column(Boolean, default=False)
    question = Column(String, nullable=True)
    answer = Column(Text, nullable=True)

    error = Column(Boolean, default=False)

Base.metadata.create_all(bind=target_engine)

def initialize_database():
    with default_engine.connect() as connection:
        with connection.execution_options(isolation_level="AUTOCOMMIT"):
            result = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = 'threads_db'")
            ).fetchone()
            if not result:
                connection.execute(text("CREATE DATABASE threads_db"))

def ensure_tables():
    Base.metadata.create_all(bind=target_engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
   
    initialize_database()
    ensure_tables()
    conn_string = DEFAULT_DATABASE_URL.replace("postgresql+psycopg", "postgresql")
    # conn_string="host=localhost port=5432 dbname=chatbot_db user=postgres password=admin"

    async with AsyncConnectionPool(
        conninfo=conn_string,
        kwargs={"autocommit": True},
        max_size=20,
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()

        human_workflow.set_checkpointer(checkpointer)

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
    question_asked: bool
    question: Optional[str] = None
    answer: Optional[str] = None
    confirmed: bool
    error: bool

class StartThreadResponse(BaseModel):
    thread_id: str

class ChatRequest(BaseModel):
    question: Optional[str] = None

class UpdateStateRequest(BaseModel):
    answer: str

@app.post("/start_thread", response_model=StartThreadResponse)
async def start_thread(db: Session = Depends(get_db)):
    thread_id = str(uuid4())
    new_thread = Thread(
        thread_id=thread_id, question_asked=False, confirmed=False, error=False
    )
    db.add(new_thread)
    db.commit()
    db.refresh(new_thread)
    return StartThreadResponse(thread_id=new_thread.thread_id)


@app.post("/ask_question/{thread_id}", response_model=ThreadResponse)
async def ask_question(
    thread_id: str, request: ChatRequest, db: Session = Depends(get_db)
):
    thread = db.query(Thread).filter(Thread.thread_id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread ID does not exist.")
    if thread.question_asked:
        raise HTTPException(
            status_code=400,
            detail=f"Question has already been asked for thread ID: {thread_id}.",
        )
    if not request.question:
        raise HTTPException(status_code=400, detail="Missing question.")
    response_state = await human_workflow.ainvoke(
        input={"message": request.question},
        config={"recursion_limit": 15, "configurable": {"thread_id": thread_id}},
        subgraphs=True,
    )
    thread.question_asked = True
    thread.question = request.question

        # Add debugging to understand the structure
 
    # print("Response state content:", response_state)
    
    thread.answer = response_state[1]["message"][-1].content
    thread.error = response_state[1].get("error", False)
    db.commit()
    return ThreadResponse(
        thread_id=thread.thread_id,
        question_asked=thread.question_asked,
        question=thread.question,
        answer=thread.answer,
        confirmed=thread.confirmed,
        error=thread.error,
    )


# Run the application if executed as the main script
if __name__ == '__main__':
    import uvicorn  # Import Uvicorn server for running the FastAPI app
    uvicorn.run(app, host='127.0.0.1', port=8001)  # Start the app on localhost with port 8000