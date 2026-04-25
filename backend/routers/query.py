import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from models.schemas import QueryRequest, QueryResponse
from service.Rag_service import answer_question, stream_answer_question
from service.Vector_store import vector_store
from auth.dependencies import get_current_user
from db import chat_repo
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


#  Non-streaming 
@router.post("/query", response_model=QueryResponse)
async def query_book(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    if not vector_store.book_exists(request.book_id):
        raise HTTPException(status_code=404, detail="Book not found. Upload it first.")
    try:
        # Fetch history for non-streaming too
        history = []
        if request.chat_id:
            history = await chat_repo.get_recent_messages(request.chat_id, limit=6)

        return await answer_question(
            book_id=request.book_id,
            question=request.question,
            history=history,          # ← was missing before
        )
    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate answer.")


#  Streaming 
@router.post("/query/stream")
async def query_book_stream(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    if not vector_store.book_exists(request.book_id):
        raise HTTPException(status_code=404, detail="Book not found. Upload it first.")

    if request.chat_id:
        chat = await chat_repo.get_chat(request.chat_id, user_id=current_user["user_id"])
        if not chat:
            raise HTTPException(status_code=403, detail="Chat not found or access denied.")

    return StreamingResponse(
        _stream_and_save(request.book_id, request.question, request.chat_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_and_save(book_id: str, question: str, chat_id: str | None):
    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    full_answer   = ""
    final_sources = None
    ai_message_id = None

    try:
        history = []
        if chat_id:
            # Fetch BEFORE saving current message so history doesn't include it
            history = await chat_repo.get_recent_messages(chat_id, limit=6)

            await chat_repo.save_message(chat_id=chat_id, role="user", text=question)
            await chat_repo.update_chat_preview(chat_id, question)

            ai_msg = await chat_repo.save_message(chat_id=chat_id, role="ai", text="")
            ai_message_id = ai_msg["message_id"]

        async for event_str in stream_answer_question(book_id, question, history=history):
            try:
                payload = json.loads(event_str.removeprefix("data: ").strip())
            except Exception:
                yield event_str
                continue

            if payload["type"] == "token":
                full_answer += payload["content"]
            elif payload["type"] == "sources":
                final_sources = payload["content"]
            elif payload["type"] == "done":
                if chat_id and ai_message_id:
                    await chat_repo.update_message(
                        message_id=ai_message_id,
                        text=full_answer,
                        sources=final_sources,
                    )
                    await chat_repo.update_chat_preview(chat_id, question)

            yield event_str

    except Exception as e:
        logger.error(f"Stream error: {e}", exc_info=True)
        yield sse({"type": "error", "content": str(e)})
        yield sse({"type": "done"})