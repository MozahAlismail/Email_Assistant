from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment variables (fallback to SQLite for local development)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./emailassistant.db")
engine = create_async_engine(DATABASE_URL, echo=True)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]: # Database session generator
    async with async_session() as session:
        yield session
