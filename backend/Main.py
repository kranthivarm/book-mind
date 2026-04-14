
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import upload, query
import logging

# All services logger.info/error ; console print
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(
    title="Textbook RAG API",
    description="Upload textbooks and ask AI questions grounded in your textbook content.",
    version="1.0.0",
    docs_url="/docs",   
    redoc_url="/redoc"  # ReDoc UI at http://localhost:8000/redoc
)


# //cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           
    allow_credentials=True,
    allow_methods=["*"],           
    allow_headers=["*"],          
)



@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "message": "Textbook RAG API is running",
        "docs": "/docs"
    }

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)