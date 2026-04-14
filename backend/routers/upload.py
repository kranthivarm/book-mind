from fastapi import APIRouter, UploadFile, File, HTTPException, status
from models.schemas import UploadResponse
from service.Pdf_service import process_pdf
from service.Embedding_service import embedding_service
from service.Vector_store import vector_store
from Config import settings
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a textbook PDF",
    description="Upload a PDF textbook. Returns a book_id used for all future queries."
)
async def upload_pdf(
    file: UploadFile = File(..., description="PDF file to upload")
):
    

    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted. Please upload a .pdf file."
        )

    # Read file into memory
    file_bytes = await file.read()

    # Check file size (convert MB limit to bytes)
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is {settings.MAX_FILE_SIZE_MB}MB."
        )

    # Extra safety: check PDF magic bytes (%PDF-)
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File does not appear to be a valid PDF."
        )

    
    book_id = str(uuid.uuid4()).replace("-", "")  # Remove hyphens for ChromaDB compat

    logger.info(f"Processing upload: {file.filename} → book_id={book_id}")

    # Extract text & chunk 
    try:
        chunks, total_pages = process_pdf(file_bytes)
    except Exception as e:
        logger.error(f"PDF processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not read PDF. Make sure it's not password-protected. Error: {str(e)}"
        )

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No readable text found in the PDF. It may be a scanned image PDF."
        )

    logger.info(f"Extracted {len(chunks)} chunks from {total_pages} pages")

    #   Generate embedding    
    chunk_texts = [chunk["text"] for chunk in chunks]

    try:
        embeddings = embedding_service.embed_texts(chunk_texts)
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embeddings. Please try again."
        )

    logger.info(f"Generated {len(embeddings)} embeddings")

    #  Store in ChromaDB
    try:
        vector_store.store_chunks(book_id, chunks, embeddings)
    except Exception as e:
        logger.error(f"Vector store failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store book in database. Please try again."
        )

    #  Return success response
    return UploadResponse(
        book_id=book_id,
        filename=file.filename,
        total_pages=total_pages,
        total_chunks=len(chunks),
        message=f"'{file.filename}' processed successfully. You can now ask questions about it."
    )