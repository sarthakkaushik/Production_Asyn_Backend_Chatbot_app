from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, String, Boolean, Text, DateTime, create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from uuid import uuid4
from contextlib import asynccontextmanager
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from fastapi.middleware.cors import CORSMiddleware
from asyncio import WindowsSelectorEventLoopPolicy
import asyncio

asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

from Chatbotflow import Chatbotflow

human_workflow = Chatbotflow()

# Database configuration
DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:admin@localhost:5432/postgres"
TARGET_DATABASE_URL = "postgresql+psycopg://postgres:admin@localhost:5432/chatbot_sessions_db"

default_engine = create_engine(DEFAULT_DATABASE_URL, future=True)
target_engine = create_engine(TARGET_DATABASE_URL, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine)
Base = declarative_base()

# Database models
class UserSession(Base):
    __tablename__ = "user_sessions"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    thread_id = Column(String, nullable=False, index=True)
    question = Column(Text, nullable=True)
    ai_answer = Column(Text, nullable=True)
    error = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

def initialize_database():
    try:
        with default_engine.connect() as connection:
            with connection.execution_options(isolation_level="AUTOCOMMIT"):
                result = connection.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = 'chatbot_sessions_db'")
                ).fetchone()
                if not result:
                    connection.execute(text("CREATE DATABASE chatbot_sessions_db"))
                    print("Database created successfully")
    except Exception as e:
        print(f"Error creating database: {e}")

def ensure_tables():
    try:
        Base.metadata.create_all(bind=target_engine)
        print("Tables created successfully")
    except Exception as e:
        print(f"Error creating tables: {e}")

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database and tables
    print("Initializing database...")
    initialize_database()
    ensure_tables()
    
    # Set up connection pool
    conn_string = DEFAULT_DATABASE_URL.replace("postgresql+psycopg", "postgresql")
    async with AsyncConnectionPool(
        conninfo=conn_string,
        kwargs={"autocommit": True},
        max_size=20,
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        human_workflow.set_checkpointer(checkpointer)
        yield

# FastAPI app setup
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models for API requests and responses
class NewSessionRequest(BaseModel):
    user_id: str

class NewSessionResponse(BaseModel):
    thread_id: str

class ContinueSessionRequest(BaseModel):
    user_id: str
    thread_id: str
    question: str

class ContinueSessionResponse(BaseModel):
    thread_id: str
    question: str
    ai_answer: str
    timestamp: datetime

# API endpoints
@app.post("/new_session", response_model=NewSessionResponse)
async def start_session(request: NewSessionRequest, db: Session = Depends(get_db)):
    try:
        thread_id = str(uuid4())
        session_entry = UserSession(
            id=str(uuid4()),
            user_id=request.user_id,
            thread_id=thread_id
        )
        db.add(session_entry)
        db.commit()
        return NewSessionResponse(thread_id=thread_id)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/continue_session", response_model=ContinueSessionResponse)
async def continue_session(request: ContinueSessionRequest, db: Session = Depends(get_db)):
    try:
        # Verify existing session
        existing_session = db.query(UserSession).filter(
            UserSession.user_id == request.user_id,
            UserSession.thread_id == request.thread_id
        ).first()

        if not existing_session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get AI response
        response_state = await human_workflow.ainvoke(
            input={"message": request.question},
            config={
                "recursion_limit": 15,
                "configurable": {"thread_id": request.thread_id}
            },
            subgraphs=True,
        )

        # Create new session entry
        new_entry = UserSession(
            id=str(uuid4()),
            user_id=request.user_id,
            thread_id=request.thread_id,
            question=request.question,
            ai_answer=response_state[1]["message"][-1].content,
            timestamp=datetime.utcnow()
        )
        db.add(new_entry)
        db.commit()

        return ContinueSessionResponse(
            thread_id=request.thread_id,
            question=request.question,
            ai_answer=new_entry.ai_answer,
            timestamp=new_entry.timestamp
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Add a new endpoint to get session history
@app.get("/session_history/{thread_id}")
async def get_session_history(thread_id: str, db: Session = Depends(get_db)):
    try:
        sessions = db.query(UserSession).filter(
            UserSession.thread_id == thread_id
        ).order_by(UserSession.timestamp).all()
        
        if not sessions:
            raise HTTPException(status_code=404, detail="No sessions found for this thread")
            
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)