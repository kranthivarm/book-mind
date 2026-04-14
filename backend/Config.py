


from pydantic_settings import BaseSettings # to automaticaly read from env
from pydantic import Field


class Settings(BaseSettings):

    GROQ_API_KEY: str = Field(..., description="Your Groq API key from console.groq.com")



    LLM_MODEL: str = "llama-3.1-8b-instant"   # Fast & smart Groq model
    LLM_TEMPERATURE: float = 0.1              # Low = more factual, less creative
    LLM_MAX_TOKENS: int = 1024                # Max tokens in the generated answer

    
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150

    TOP_K_RESULTS: int = 5

    
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    
    MAX_FILE_SIZE_MB: int = 50

    class Config:
        env_file = ".env"


# Single global instance — import this everywhere
settings = Settings()