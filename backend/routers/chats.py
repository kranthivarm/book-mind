from fastapi import APIRouter, HTTPException, status
from models.schemas import ChatOut, MessageOut, CreateChatRequest
from db import chat_repo
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chats", tags=["Chats"])


@router.get("", response_model=list[ChatOut])
async def list_chats():
    return await chat_repo.get_all_chats()


@router.post("", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
async def create_chat(body: CreateChatRequest):
    
    chat = await chat_repo.create_chat(
        book_id=body.book_id,
        book_name=body.book_name,
        total_pages=body.total_pages,
        total_chunks=body.total_chunks,
    )
    logger.info(f"Chat created: {chat['chat_id']} → book {body.book_id}")
    return chat


@router.get("/{chat_id}", response_model=ChatOut)
async def get_chat(chat_id: str):
    chat = await chat_repo.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: str):
    chat = await chat_repo.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    await chat_repo.delete_chat(chat_id)
    logger.info(f"Chat deleted: {chat_id}")


@router.get("/{chat_id}/messages", response_model=list[MessageOut])
async def get_messages(chat_id: str):
    chat = await chat_repo.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return await chat_repo.get_messages(chat_id)