from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, UTC
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.sql import text

load_dotenv()

# Database configuration
DEFAULT_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@localhost:5432/postgres")
TARGET_DATABASE_URL = os.getenv("TARGET_DATABASE_URL", "postgresql://admin:admin@localhost:5432/chatbot_db")

# Create SQLAlchemy engines
default_engine = create_engine(DEFAULT_DATABASE_URL, future=True)
target_engine = create_engine(TARGET_DATABASE_URL, future=True)

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=target_engine)

class Thread(Base):
    __tablename__ = "threads"
    
    thread_id = Column(String, primary_key=True, index=True)
    question_asked = Column(Boolean, default=False)
    question = Column(String, nullable=True)
    answer = Column(Text, nullable=True)
    confirmed = Column(Boolean, default=False)
    error = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))

def initialize_database():
    with default_engine.connect() as connection:
        with connection.execution_options(isolation_level="AUTOCOMMIT"):
            # Check if database exists
            result = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = 'chatbot_db'")
            ).fetchone()
            if not result:
                connection.execute(text("CREATE DATABASE chatbot_db"))

def ensure_tables():
    Base.metadata.create_all(bind=target_engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@asynccontextmanager
async def get_async_pool():
    conn_string = DEFAULT_DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
    async with AsyncConnectionPool(
        conninfo=conn_string,
        kwargs={"autocommit": True},
        max_size=20,
    ) as pool:
        yield pool 