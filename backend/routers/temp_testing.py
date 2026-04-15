from fastapi import APIRouter, HTTPException, status
from service.Vector_store import vector_store
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats", description="Collection stats — all books in the shared collection.Returns total chunk count and per-book breakdown.Useful for debugging and monitoring.")
async def collection_stats():
    
    try:
        return vector_store.collection_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/books", description="List all book_ids in the collection")
async def list_books():
    try:
        return {"books": vector_store.list_books()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/books/{book_id}", description="Delete a book from the collection")
async def delete_book(book_id: str):
    success = vector_store.delete_book(book_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return {"message": f"Book {book_id} deleted successfully"}