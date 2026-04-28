from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from models.schemas import UploadResponse
from service.Pdf_service import process_pdf
from service.Embedding_service import embedding_service
from service.Vector_store import vector_store
from auth.dependencies import get_current_user
from Config import settings
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    # Validate file type
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted.",
        )

    file_bytes = await file.read()

    # Validate size
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Max size is {settings.MAX_FILE_SIZE_MB}MB.",
        )

    # Validate PDF magic bytes
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not a valid PDF.",
        )

    book_id = str(uuid.uuid4()).replace("-", "")
    logger.info(f"Upload: {file.filename} → book_id={book_id} | user={current_user['user_id']}")

    try:
        chunks, total_pages = process_pdf(file_bytes)
    except Exception as e:
        logger.error(f"PDF processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not read PDF: {str(e)}",
        )

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No readable text found in PDF. It may be a scanned image.",
        )

    logger.info(f"Extracted {len(chunks)} chunks from {total_pages} pages")

    try:
        chunk_texts = [c["text"] for c in chunks]
        embeddings  = embedding_service.embed_texts(chunk_texts)
        vector_store.store_chunks(book_id, chunks, embeddings)
    except Exception as e:
        logger.error(f"Embedding/storage error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process embeddings: {str(e)}",
        )

    return UploadResponse(
        book_id=book_id,
        filename=file.filename,
        total_pages=total_pages,
        total_chunks=len(chunks),
        message=f"'{file.filename}' processed successfully.",
    )