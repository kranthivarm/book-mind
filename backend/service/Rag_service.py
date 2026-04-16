from groq import Groq
from typing import List, Dict, AsyncGenerator
from Config import settings
from service.Embedding_service import embedding_service
from service.Vector_store import vector_store
from models.schemas import QueryResponse, SourceChunk
import logging
import math
import json
import re

logger = logging.getLogger(__name__)

groq_client = Groq(api_key=settings.GROQ_API_KEY)

SYSTEM_PROMPT = """You are an expert educational tutor for school students.
Your ONLY job is to answer questions based on the textbook excerpts provided.

STRICT RULES:
1. Answer ONLY using information from the provided textbook context below.
2. If the answer is not found in the context, say: "I couldn't find this topic in the uploaded textbook. Please check another chapter or ask your teacher."
3. Do NOT use any outside knowledge — even if you know the answer.
4. Use clear, simple language suitable for school students.
5. When possible, reference specific parts of the text in your explanation.
6. Keep answers concise but complete."""

HUMAN_PROMPT_TEMPLATE = """Here are the relevant excerpts from the student's textbook:

{context}

---

Student's Question: {question}

Please answer the question based ONLY on the textbook excerpts above."""



def build_context_string(retrieved_chunks: List[Dict]) -> str:
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks):
        page = chunk["metadata"]["page_number"]
        text = chunk["text"]
        context_parts.append(f"[Page {page}, Excerpt {i+1}]\n{text}")
    return "\n\n".join(context_parts)


def parse_raw_results(raw_results: Dict) -> List[Dict]:
    documents = raw_results["documents"][0]
    metadatas = raw_results["metadatas"][0]
    distances = raw_results["distances"][0]
    return [
        {"text": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]


def distance_to_score(distance: float) -> float:
    score = 1.0 - (distance / 2.0)
    return round(max(0.0, min(1.0, score)), 3)


def normalise_rerank_score(raw_score: float) -> float:
    return round(1 / (1 + math.exp(-raw_score)), 3)


def _build_sources(top_chunks: List[Dict]) -> List[SourceChunk]:
    """Shared by both answer_question and stream_answer_question."""
    sources = []
    for chunk in top_chunks:
        score   = normalise_rerank_score(chunk.get("rerank_score", 0))
        preview = chunk["text"][:200] + ("..." if len(chunk["text"]) > 200 else "")
        preview = re.sub(r"^\[Context from previous section:.*?\]\n\n", "", preview, flags=re.DOTALL)
        sources.append(SourceChunk(
            page_number=chunk["metadata"]["page_number"],
            chunk_index=chunk["metadata"]["chunk_index"],
            text_preview=preview.strip(),
            relevance_score=score,
        ))
    return sources


def _get_top_chunks(book_id: str, question: str) -> List[Dict]:
    """
    Shared retrieval + reranking used by both functions.
    Returns reranked top chunks, or empty list if nothing found.
    """
    logger.info(f"Embedding question for book_id={book_id}")
    query_vector = embedding_service.embed_query(question)

    logger.info(f"Retrieving top {settings.RERANK_CANDIDATES} candidates from ChromaDB")
    raw_results = vector_store.search(
        book_id=book_id,
        query_embedding=query_vector,
        top_k=settings.RERANK_CANDIDATES,
    )

    candidates = parse_raw_results(raw_results)
    if not candidates:
        return []

    logger.info("Reranking candidates with cross-encoder")
    top_chunks = embedding_service.rerank(
        query=question,
        chunks=candidates,
        top_n=settings.TOP_K_RESULTS,
    )
    return top_chunks


# //non streaming
async def answer_question(book_id: str, question: str) -> QueryResponse:
    top_chunks = _get_top_chunks(book_id, question)

    if not top_chunks:
        return QueryResponse(
            answer="No relevant content found in the textbook for your question.",
            sources=[],
            question=question
        )

    context_string = build_context_string(top_chunks)
    human_message  = HUMAN_PROMPT_TEMPLATE.format(context=context_string, question=question)

    logger.info(f"Calling Groq LLM (model={settings.LLM_MODEL})")
    completion = groq_client.chat.completions.create(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": human_message}
        ]
    )

    answer_text = completion.choices[0].message.content.strip()
    logger.info("Groq LLM response received")

    return QueryResponse(answer=answer_text, sources=_build_sources(top_chunks), question=question)


#  Streaming 

async def stream_answer_question(book_id: str, question: str) -> AsyncGenerator[str, None]:   

    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    try:
        #  Retrieval + reranking (same as answer_question)
        yield sse({"type": "status", "content": "Searching your textbook…"})

        top_chunks = _get_top_chunks(book_id, question)

        if not top_chunks:
            yield sse({"type": "error", "content": "No relevant content found in the textbook for your question."})
            yield sse({"type": "done"})
            return

        context_string = build_context_string(top_chunks)
        human_message  = HUMAN_PROMPT_TEMPLATE.format(context=context_string, question=question)

        #   Groq streaming call
        # Only difference from answer_question: stream=True
        yield sse({"type": "status", "content": "Generating answer…"})

        logger.info(f"Calling Groq LLM streaming (model={settings.LLM_MODEL})")
        stream = groq_client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            stream=True,                          # ← only change from non-streaming
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": human_message}
            ]
        )

        #   Yield each token as it arrives from Groq 
        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield sse({"type": "token", "content": token})

        #   Send sources after answer is complete  
        sources_data = [
            {
                "page_number":     s.page_number,
                "chunk_index":     s.chunk_index,
                "text_preview":    s.text_preview,
                "relevance_score": s.relevance_score,
            }
            for s in _build_sources(top_chunks)
        ]
        yield sse({"type": "sources", "content": sources_data})
        yield sse({"type": "done"})

    except Exception as e:
        logger.error(f"Streaming error: {e}", exc_info=True)
        yield sse({"type": "error", "content": str(e)})
        yield sse({"type": "done"})