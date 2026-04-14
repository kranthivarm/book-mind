# Converts text into embedding vectors using a local sentence-transformers model.

from sentence_transformers import SentenceTransformer
from typing import List
from Config import settings
import logging

logger = logging.getLogger(__name__)


class EmbeddingService: #singleton

    def __init__(self):
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        # This downloads the model on first run (~22MB), then caches locally
        self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Embedding model loaded successfully")


    def embed_texts(self, texts: List[str]) -> List[List[float]]: #batch processing for faster embedding

        embeddings = self._model.encode(
            texts,
            batch_size=32,           # Process 32 chunks at once
            show_progress_bar=False,
            convert_to_numpy=True    # ChromaDB expects numpy arrays or lists
        )
        # Convert numpy array to Python list (JSON-serializable)
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        
        vector = self._model.encode(query, convert_to_numpy=True)
        return vector.tolist()

#singleton
embedding_service = EmbeddingService()