from fastapi import APIRouter, HTTPException, status, Depends
from models.schemas import ChatOut, MessageOut, CreateChatRequest
from auth.dependencies import get_current_user
from db import chat_repo
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chats", tags=["Chats"])


@router.get("", response_model=list[ChatOut])
async def list_chats(current_user: dict = Depends(get_current_user)):
    return await chat_repo.get_all_chats(user_id=current_user["user_id"])


@router.post("", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
async def create_chat(body: CreateChatRequest, current_user: dict = Depends(get_current_user)):
    chat = await chat_repo.create_chat(
        user_id=current_user["user_id"],
        book_id=body.book_id,
        book_name=body.book_name,
        total_pages=body.total_pages,
        total_chunks=body.total_chunks,
    )
    logger.info(f"Chat created: {chat['chat_id']} for user {current_user['user_id']}")
    return chat


@router.get("/{chat_id}", response_model=ChatOut)
async def get_chat(chat_id: str, current_user: dict = Depends(get_current_user)):
    chat = await chat_repo.get_chat(chat_id, user_id=current_user["user_id"])
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")
    return chat


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: str, current_user: dict = Depends(get_current_user)):
    chat = await chat_repo.get_chat(chat_id, user_id=current_user["user_id"])
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")
    await chat_repo.delete_chat(chat_id, user_id=current_user["user_id"])


@router.get("/{chat_id}/messages", response_model=list[MessageOut])
async def get_messages(chat_id: str, current_user: dict = Depends(get_current_user)):
    # Verify chat belongs to this user before returning messages
    chat = await chat_repo.get_chat(chat_id, user_id=current_user["user_id"])
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")
    return await chat_repo.get_messages(chat_id)