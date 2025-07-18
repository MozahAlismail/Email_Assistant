from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import create_db_and_tables
from routes import email_router, log_router

async def lifespan(app):
    await create_db_and_tables()
    yield

app = FastAPI(title="Email Assistant", lifespan=lifespan)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the HTML interface at root
@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

# Include API routes
app.include_router(email_router, prefix="/generate", tags=["Email"])
app.include_router(log_router, prefix="/logs", tags=["Logs"])
