from pydantic import BaseModel, Field
from typing import List


class UploadResponse(BaseModel):    
    book_id: str = Field(..., description="Unique ID for this book in ChromaDB")
    filename: str = Field(..., description="Original filename of the uploaded PDF")
    total_pages: int = Field(..., description="Number of pages extracted from the PDF")
    total_chunks: int = Field(..., description="Number of text chunks stored in vector DB")
    message: str = Field(..., description="Human-readable success message")


class QueryRequest(BaseModel):    
    book_id: str = Field(..., description="ID of the book to search in")
    question: str = Field(..., min_length=3, description="The student's question")


class SourceChunk(BaseModel):    
    page_number: int = Field(..., description="Page in the original PDF")
    chunk_index: int = Field(..., description="Which chunk on that page (0-based)")
    text_preview: str = Field(..., description="First 200 chars of the chunk text")
    relevance_score: float = Field(..., description="Similarity score 0–1 (higher = more relevant)")


class QueryResponse(BaseModel):
   
    answer: str = Field(..., description="LLM-generated answer based on the textbook")
    sources: List[SourceChunk] = Field(..., description="Textbook chunks used to generate the answer")
    question: str = Field(..., description="Echo of the original question")


class ErrorResponse(BaseModel):
    detail: str