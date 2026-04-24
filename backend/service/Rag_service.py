from groq import AsyncGroq, Groq
from typing import List, Dict, AsyncGenerator, Optional
from Config import settings
from service.Embedding_service import embedding_service
from service.Vector_store import vector_store
from models.schemas import QueryResponse, SourceChunk
import logging
import math
import json
import re

logger = logging.getLogger(__name__)

sync_groq_client  = Groq(api_key=settings.GROQ_API_KEY)
async_groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)



SYSTEM_PROMPT = """You are an expert educational tutor for school students.
Answer questions ONLY from the textbook excerpts provided below.

STRICT RULES:
1. Use ONLY the provided textbook context. Never use outside knowledge.
2. If the answer is not in the context, say: "I couldn't find this topic in the uploaded textbook. Please check another chapter or ask your teacher."
3. Use clear, simple language suitable for school students.
4. You have access to the recent conversation history — use it to understand follow-up questions and references like "it", "that", "explain more", "why?".
5. Keep answers concise but complete."""

HUMAN_PROMPT_TEMPLATE = """Here are the relevant excerpts from the student's textbook:

{context}

---

Student's Question: {question}

If the question contains pronouns like "it", "that", "they", etc resolve them using the conversation history before answering.

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


def normalise_rerank_score(raw_score: float) -> float:
    return round(1 / (1 + math.exp(-raw_score)), 3)


def _build_sources(top_chunks: List[Dict]) -> List[SourceChunk]:
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


#  Chat history helpers

def build_history_messages(history: List[Dict]) -> List[Dict]:
    
    # Take only last N messages, skip empty AI placeholders # last 3 only
    recent = [m for m in history if m.get("text", "").strip()]
    recent = recent[-settings.HISTORY_MESSAGES_LIMIT:]

    groq_messages = []
    for msg in recent:
        role = "assistant" if msg["role"] == "ai" else "user"
        groq_messages.append({"role": role, "content": msg["text"]})

    # print(groq_messages)
    
    return groq_messages


def build_retrieval_query(question: str, history: List[Dict]) -> str:
    """
    Combines current question + last user question for better embedding search.
    """
    # Find the last user question from history
    last_user_q = ""
    for msg in reversed(history):
        if msg.get("role") == "user" and msg.get("text", "").strip():
            last_user_q = msg["text"].strip()
            break

    if last_user_q and last_user_q.lower() != question.lower():
        # Combine: last question gives semantic context, current gives intent
        return f"{last_user_q} {question}"

    return question

# def build_retrieval_query(question: str, history: List[Dict]) -> str:
#     last_user_msgs = [
#         m["text"] for m in reversed(history)
#         if m.get("role") == "user" and m.get("text", "").strip()
#     ][:2]

#     last_user_msgs.reverse()

#     return " ".join(last_user_msgs + [question])


def _get_top_chunks(book_id: str, question: str, history: List[Dict] = None) -> List[Dict]:
    """
    Retrieval + reranking.
    Uses history-aware query for embedding if history is provided.
    """
    # Build a richer query using conversation context
    retrieval_query = build_retrieval_query(question, history or [])

    if retrieval_query != question:
        logger.info(f"History-aware query: '{retrieval_query[:80]}'")

    query_vector = embedding_service.embed_query(retrieval_query)

    raw_results = vector_store.search(
        book_id=book_id,
        query_embedding=query_vector,
        top_k=settings.RERANK_CANDIDATES,
    )

    candidates = parse_raw_results(raw_results)
    if not candidates:
        return []

    top_chunks = embedding_service.rerank(
        query=question,      # rerank against original question, not expanded query
        chunks=candidates,
        top_n=settings.TOP_K_RESULTS,
    )
    return top_chunks


#   LLM messages builder  

def build_llm_messages(
    context_string: str,
    question: str,
    history_messages: List[Dict],
) -> List[Dict]:
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Insert conversation history BEFORE the current question
    messages.extend(history_messages)

    # Current question with textbook context
    human_message = HUMAN_PROMPT_TEMPLATE.format(
        context=context_string,
        question=question,
    )
    messages.append({"role": "user", "content": human_message})

    return messages


#   Non-streaming  

async def answer_question(
    book_id: str,
    question: str,
    history: Optional[List[Dict]] = None,
) -> QueryResponse:
    history = history or []
    top_chunks = _get_top_chunks(book_id, question, history)

    if not top_chunks:
        return QueryResponse(
            answer="No relevant content found in the textbook for your question.",
            sources=[], question=question
        )

    context_string   = build_context_string(top_chunks)
    history_messages = build_history_messages(history)
    messages         = build_llm_messages(context_string, question, history_messages)

    logger.info(f"Calling Groq | model={settings.LLM_MODEL} | history_turns={len(history_messages)//2}")
    completion = sync_groq_client.chat.completions.create(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        messages=messages,
    )

    answer_text = completion.choices[0].message.content.strip()
    return QueryResponse(answer=answer_text, sources=_build_sources(top_chunks), question=question)


#   Streaming  

async def stream_answer_question(
    book_id: str,
    question: str,
    history: Optional[List[Dict]] = None,
) -> AsyncGenerator[str, None]:
    history = history or []

    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    try:
        yield sse({"type": "status", "content": "Searching your textbook…"})

        top_chunks = _get_top_chunks(book_id, question, history)

        if not top_chunks:
            yield sse({"type": "error", "content": "No relevant content found in the textbook for your question."})
            yield sse({"type": "done"})
            return

        context_string   = build_context_string(top_chunks)
        history_messages = build_history_messages(history)
        messages         = build_llm_messages(context_string, question, history_messages)

        yield sse({"type": "status", "content": "Generating answer…"})

        logger.info(f"Groq stream | model={settings.LLM_MODEL} | history_turns={len(history_messages)//2}")

        stream = await async_groq_client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            stream=True,
            messages=messages,
        )

        async for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield sse({"type": "token", "content": token})

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