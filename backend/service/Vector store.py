import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any
from Config import settings
import logging

logger = logging.getLogger(__name__)


class VectorStore:

    def __init__(self):

        self._client = chromadb.PersistentClient(# // to save to disk ; else will be lost at restart
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False)  # Disable analytics
        )
        logger.info(f"ChromaDB initialized at: {settings.CHROMA_PERSIST_DIR}")

    def _get_collection(self, book_id: str):
        
        return self._client.get_or_create_collection(
            name=f"book_{book_id}",   # Prefix to avoid name collision
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )

    def store_chunks(
        self,
        book_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
         

        collection = self._get_collection(book_id)

        # Build the 4 parallel lists ChromaDB expects
        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{book_id}_page{chunk['page_number']}_chunk{chunk['chunk_index']}"
            ids.append(chunk_id)
            documents.append(chunk["text"])
            metadatas.append({
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"],
                "char_start": chunk["char_start"],
                "char_end": chunk["char_end"]
            })

        # ChromaDB batches upserts internally, but we chunk manually
        # to avoid memory issues with very large books (1000+ chunks)
        BATCH_SIZE = 100
        for batch_start in range(0, len(ids), BATCH_SIZE):
            batch_end = batch_start + BATCH_SIZE
            collection.add(
                ids=ids[batch_start:batch_end],
                documents=documents[batch_start:batch_end],
                embeddings=embeddings[batch_start:batch_end],
                metadatas=metadatas[batch_start:batch_end]
            )
            logger.info(f"Stored batch {batch_start}–{batch_end} for book {book_id}")

        logger.info(f"Stored {len(chunks)} chunks for book_id={book_id}")

    def search(
        self,
        book_id: str,
        query_embedding: List[float],
        top_k: int = None
    ) -> Dict[str, Any]:                

        if top_k is None:
            top_k = settings.TOP_K_RESULTS

        collection = self._get_collection(book_id)

        results = collection.query(
            query_embeddings=[query_embedding],  # Must be a list of vectors
            n_results=min(top_k, collection.count()),  # Can't ask for more than we have
            include=["documents", "metadatas", "distances"]
        )

        return results
    


    def book_exists(self, book_id: str) -> bool:
        
        try:
            collection = self._client.get_collection(f"book_{book_id}")
            return collection.count() > 0
        except Exception:
            return False

    def delete_book(self, book_id: str) -> bool:
        
        try:
            self._client.delete_collection(f"book_{book_id}")
            logger.info(f"Deleted collection for book_id={book_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete book {book_id}: {e}")
            return False


vector_store = VectorStore()