from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from models.schemas import QueryRequest, QueryResponse
from service.Rag_service import answer_question, stream_answer_question
from service.Vector_store import vector_store
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Ask a question about a textbook",
    description="Send a question and book_id. Returns an AI-generated answer with source references."
)
async def query_book(request: QueryRequest):
    
    if not vector_store.book_exists(request.book_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id '{request.book_id}' not found. Please upload the PDF first."
        )

    logger.info(f"Query received: book_id={request.book_id}, question='{request.question[:50]}...'")


    #  Run RAG pipeline 
    try:
        response = await answer_question(
            book_id=request.book_id,
            question=request.question
        )
    except Exception as e:
        logger.error(f"RAG pipeline error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the answer. Please try again."
        )

    return response


# //streaming
@router.post(
    "/query/stream",
    summary="Ask a question (streaming SSE response)",
)
async def query_book_stream(request: QueryRequest):
    if not vector_store.book_exists(request.book_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id '{request.book_id}' not found. Please upload the PDF first."
        )
    logger.info(f"Stream query: book_id={request.book_id}, question='{request.question[:50]}...'")
 
    return StreamingResponse(
        stream_answer_question(book_id=request.book_id, question=request.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",       # prevents nginx from buffering the stream
        },
    )
 