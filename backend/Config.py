from pydantic_settings import BaseSettings # to automaticaly read from env
from pydantic import Field


class Settings(BaseSettings):

    GROQ_API_KEY: str = Field(..., description="Your Groq API key from console.groq.com")


    anonymized_telemetry: bool = Field(default=False)

    DATABASE_URL: str = Field(..., description="PostgreSQL connection string")

    SECRET_KEY:    str = Field(..., description="Strong random secret for JWT signing")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES:  int = 15
    REFRESH_TOKEN_EXPIRE_DAYS:    int = 7

    COOKIE_SECURE: bool = False

    LLM_MODEL: str = "llama-3.1-8b-instant"   # Fast & smart Groq model
    LLM_TEMPERATURE: float = 0.1              # Low = more factual, less creative
    LLM_MAX_TOKENS: int = 1024                # Max tokens in the generated answer

    
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"    
    # RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-12-v2"  # 12-layer, more accurate

    
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150


    RERANK_CANDIDATES: int = 15 
    TOP_K_RESULTS: int = 5

    
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    
    # MAX_FILE_SIZE_MB: int = 50
    MAX_FILE_SIZE_MB: int = 200

    HISTORY_MESSAGES_LIMIT: int = 6


    class Config:
        env_file = ".env"


# Single global instance — import this everywhere
settings = Settings()