# routers/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from models.schemas import UploadResponse
from service.Pdf_service import process_pdf
from service.Embedding_service import embedding_service
from service.Vector_store import vector_store
from auth.dependencies import get_current_user
from Config import settings
import uuid, logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),   # ← requires login
):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    file_bytes = await file.read()

    if len(file_bytes) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Max size is {settings.MAX_FILE_SIZE_MB}MB.")

    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="File is not a valid PDF.")

    book_id = str(uuid.uuid4()).replace("-", "")
    logger.info(f"Upload: {file.filename} → book_id={book_id} | user={current_user['user_id']}")

    try:
        chunks, total_pages = process_pdf(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read PDF: {e}")

    if not chunks:
        raise HTTPException(status_code=422, detail="No readable text found in PDF.")

    chunk_texts = [c["text"] for c in chunks]
    embeddings  = embedding_service.embed_texts(chunk_texts)
    vector_store.store_chunks(book_id, chunks, embeddings)

    return UploadResponse(
        book_id=book_id,
        filename=file.filename,
        total_pages=total_pages,
        total_chunks=len(chunks),
        message=f"'{file.filename}' processed successfully.",
    )