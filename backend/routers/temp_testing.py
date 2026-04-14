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
    "/testing",
   description="just for tesating api working"
)
async def testing ():
    try:
        listOfBooks=vector_store.list_books();
        logger.info(listOfBooks[0]);

        vector_store.testing(listOfBooks[0].replace("book_",""))

        return {
            # "message": f"Printed DB contents for book_id={book_id} (check logs)"
        }
    
    except Exception as e:
        logger.error(f"Vector store failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store book in database. Please try again."
        )        
    
