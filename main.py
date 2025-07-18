import os
import sys

from fastapi import FastAPI
from database import create_db_and_tables
from routes import email_router, log_router
from pydantic_settings import BaseSettings
from fastapi.logger import logger

import nest_asyncio
import uvicorn


async def lifespan(app):
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(email_router, prefix="/generate", tags=["Email"])
app.include_router(log_router, prefix="/logs", tags=["Logs"])
