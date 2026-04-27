# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db, close_db
from routers import upload, query, chats, auth, quiz
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="BookMind API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",                       # local
        "https://bookmind-frontend.onrender.com"       # production
    ],
    allow_credentials=True,   # REQUIRED for cookies to be sent cross-origin
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,   prefix="/api")
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(query.router,  prefix="/api", tags=["Query"])
app.include_router(chats.router,  prefix="/api", tags=["Chats"])
app.include_router(quiz.router,   prefix="/api", tags=["Quiz"])  

@app.get("/")
async def root():
    return {"status": "ok"}