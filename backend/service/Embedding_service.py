# Converts text into embedding vectors using a local sentence-transformers model.

from sentence_transformers import SentenceTransformer,CrossEncoder
from typing import List,Tuple
from Config import settings
import logging

logger = logging.getLogger(__name__)


class EmbeddingService: #singleton

    def __init__(self):
        # logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        # # This downloads the model on first run (~22MB), then caches locally
        # self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
        # logger.info("Embedding model loaded successfully")
        logger.info(f"Loading bi-encoder: {settings.EMBEDDING_MODEL}")
        self._bi_encoder = SentenceTransformer(settings.EMBEDDING_MODEL)

        logger.info(f"Loading cross-encoder: {settings.RERANKER_MODEL}")
        self._cross_encoder = CrossEncoder(settings.RERANKER_MODEL)
 
        logger.info("Both models loaded successfully")



    def embed_texts(self, texts: List[str]) -> List[List[float]]: #batch processing for faster embedding

        # embeddings = self._model.encode(
        embeddings = self._bi_encoder.encode(
            texts,
            batch_size=32,           # Process 32 chunks at once
            show_progress_bar=False,
            convert_to_numpy=True    # ChromaDB expects numpy arrays or lists
        )
        # Convert numpy array to Python list (JSON-serializable)
        return embeddings.tolist()



    def embed_query(self, query: str) -> List[float]:
        # vector = self._model.encode(query, convert_to_numpy=True)
        vector = self._bi_encoder.encode(query, convert_to_numpy=True)
        return vector.tolist()
    

    
    def rerank(
        self,
        query: str,
        chunks: List[dict],
        top_n: int = None,
    ) -> List[dict]:
       
        if top_n is None:
            top_n = settings.TOP_K_RESULTS 
 
        if not chunks:
            return []
 
        # Build (query, passage) pairs for the cross-encoder
        pairs: List[Tuple[str, str]] = [(query, chunk["text"]) for chunk in chunks]
 
        # Score all pairs — returns numpy array of floats
        scores = self._cross_encoder.predict(pairs, show_progress_bar=False)
 
        # Attach score to each chunk
        for chunk, score in zip(chunks, scores):
            chunk["rerank_score"] = float(score)
 
        # Sort by rerank_score descending (most relevant first)
        reranked = sorted(chunks, key=lambda c: c["rerank_score"], reverse=True)
 
        logger.info(
            f"Reranked {len(chunks)} candidates → keeping top {top_n}. "
            f"Top score: {reranked[0]['rerank_score']:.3f}"
        )
 
        return reranked[:top_n]



#singleton
embedding_service = EmbeddingService()