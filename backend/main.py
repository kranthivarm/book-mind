from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db, close_db
from routers import upload, query, chats
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB pool and create tables
    await init_db()
    yield
    # Shutdown: close pool cleanly
    await close_db()


app = FastAPI(title="BookMind API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(query.router,  prefix="/api", tags=["Query"])
app.include_router(chats.router,  prefix="/api", tags=["Chats"])   # ← new

@app.get("/")
async def root():
    return {"status": "ok", "docs": "/docs"}