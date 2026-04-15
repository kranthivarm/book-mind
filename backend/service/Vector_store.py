import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any
from Config import settings
import logging

logger = logging.getLogger(__name__)

COLLECTION_NAME="textbooks"

class VectorStore:

    def __init__(self):

        self._client = chromadb.PersistentClient(# // to save to disk ; else will be lost at restart
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False)  # Disable analytics
        )

        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

        logger.info(
            f"VectorStore ready | collection='{COLLECTION_NAME}' | "
            f"total chunks: {self._collection.count()}"
        )    

    def store_chunks(
        self,
        book_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
                 
        # Build the 4 parallel lists ChromaDB expects
        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            # ID must be globally unique across ALL books
            chunk_id = f"{book_id}_p{chunk['page_number']}_c{chunk['chunk_index']}"
            ids.append(chunk_id)
            documents.append(chunk["text"])
            metadatas.append({
                "book_id":     book_id,           # ← key field for filtering
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"],
                "char_start":  chunk["char_start"],
                "char_end":    chunk["char_end"],
            })

        # ChromaDB batches upserts internally, but we chunk manually
        # to avoid memory issues with very large books (1000+ chunks)
        BATCH_SIZE = 100
        for batch_start in range(0, len(ids), BATCH_SIZE):            
            self._collection.add(
                ids=ids[batch_start:batch_start + BATCH_SIZE],
                documents=documents[batch_start:batch_start + BATCH_SIZE],
                embeddings=embeddings[batch_start:batch_start + BATCH_SIZE],
                metadatas=metadatas[batch_start:batch_start + BATCH_SIZE],
            )
            # logger.info(f"Stored batch {batch_start}–{batch_end} for book {book_id}")

        logger.info(f"Stored {len(chunks)} chunks for book_id={book_id}")

    def search(
        self,
        book_id: str,
        query_embedding: List[float],
        top_k: int = None
    ) -> Dict[str, Any]:                

        if top_k is None:
            top_k = settings.TOP_K_RESULTS

        # collection = self._get_collection(book_id)

        # results = collection.query(
        #     query_embeddings=[query_embedding],  # Must be a list of vectors
        #     n_results=min(top_k, collection.count()),  # Can't ask for more than we have
        #     include=["documents", "metadatas", "distances"]
        # )
        book_chunk_count = self._count_book_chunks(book_id)
        if book_chunk_count == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
 
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, book_chunk_count),
            where={"book_id": book_id},          # ← isolation filter
            include=["documents", "metadatas", "distances"],
        )
        return results
    

    def _count_book_chunks(self, book_id: str) -> int:        
        try:
            result = self._collection.get(
                where={"book_id": book_id},
                include=[],   # we only need the count, not the data
            )
            return len(result["ids"])
        except Exception:
            return 0

    def book_exists(self, book_id: str) -> bool:        
        # try:
        #     collection = self._client.get_collection(f"book_{book_id}")
        #     return collection.count() > 0
        # except Exception:
        #     return False
        return self._count_book_chunks(book_id) > 0

    def delete_book(self, book_id: str) -> bool:
        
        try:
            # self._client.delete_collection(f"book_{book_id}")
            # logger.info(f"Deleted collection for book_id={book_id}")
            self._collection.delete(where={"book_id": book_id})
            logger.info(f"Deleted all chunks for book_id={book_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete book {book_id}: {e}")
            return False
        


    
    #for testing only
    def list_books(self) -> List[str]:        
        try:
            result = self._collection.get(include=["metadatas"])
            book_ids = list({m["book_id"] for m in result["metadatas"]})
            return book_ids
        except Exception:
            return []
 
    def collection_stats(self) -> Dict:        
        try:
            result = self._collection.get(include=["metadatas"])
            counts: Dict[str, int] = {}
            for m in result["metadatas"]:
                bid = m["book_id"]
                counts[bid] = counts.get(bid, 0) + 1
            return {
                "total_chunks": self._collection.count(),
                "total_books":  len(counts),
                "books":        counts,
            }
        except Exception as e:
            return {"error": str(e)}
        

vector_store = VectorStore()