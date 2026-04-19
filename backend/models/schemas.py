from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime


#   Existing schemas 

class UploadResponse(BaseModel):
    book_id:      str
    filename:     str
    total_pages:  int
    total_chunks: int
    message:      str

class QueryRequest(BaseModel):
    book_id:  str
    question: str = Field(..., min_length=3)
    chat_id:  Optional[str] = None   # links query to a chat for saving to Postgres

class SourceChunk(BaseModel):
    page_number:     int
    chunk_index:     int
    text_preview:    str
    relevance_score: float

class QueryResponse(BaseModel):
    answer:   str
    sources:  List[SourceChunk]
    question: str

class ErrorResponse(BaseModel):
    detail: str


#  Chat schemas

class ChatOut(BaseModel):
    chat_id:      str
    book_id:      str
    book_name:    str
    total_pages:  int
    total_chunks: int
    created_at:   datetime
    last_message: str
    last_at:      datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    """A single message returned from GET /chats/{chat_id}/messages."""
    message_id: str
    chat_id:    str
    role:       str
    text:       str
    sources:    Optional[List[Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CreateChatRequest(BaseModel):
    book_id:      str
    book_name:    str
    total_pages:  int
    total_chunks: int


class SaveMessageRequest(BaseModel):
    chat_id:  str
    role:     str
    text:     str
    sources:  Optional[List[Any]] = None