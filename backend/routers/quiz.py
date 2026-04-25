# routers/quiz.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from auth.dependencies import get_current_user
from service.Vector_store import vector_store
from service.Rag_service import generate_quiz
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class QuizRequest(BaseModel):
    book_id:       str
    topic:         str = Field(..., min_length=3)
    num_questions: int = Field(default=5, ge=2, le=10)


@router.post("/quiz")
async def create_quiz(
    request: QuizRequest,
    current_user: dict = Depends(get_current_user),
):
    if not vector_store.book_exists(request.book_id):
        raise HTTPException(status_code=404, detail="Book not found. Upload it first.")

    result = await generate_quiz(
        book_id=request.book_id,
        topic=request.topic,
        num_questions=request.num_questions,
    )

    if result.get("error"):
        raise HTTPException(status_code=422, detail=result["error"])

    return result