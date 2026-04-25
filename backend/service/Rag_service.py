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


#  Prompts 

SYSTEM_PROMPT = """You are an expert educational tutor for school students.
Answer questions ONLY from the textbook excerpts provided below.

STRICT RULES:
1. Use ONLY the provided textbook context. Never use outside knowledge.
2. If the answer is not in the context, say: "I couldn't find this topic in the uploaded textbook. Please check another chapter or ask your teacher."
3. Use clear, simple language suitable for school students.
4. You have access to the recent conversation history — use it to understand follow-up questions and references like "it", "that", "explain more", "why?".
5. Keep answers concise but complete.
6. NEVER mention page numbers, excerpt numbers, or phrases like "according to excerpt 1" or "as mentioned in page X" in your answer. Just answer directly like a teacher would speak to a student. Sources are shown separately — do not reference them in text."""

HUMAN_PROMPT_TEMPLATE = """Here are the relevant excerpts from the student's textbook:

{context}

---

Student's Question: {question}

If the question contains pronouns like "it", "that", "they", resolve them using the conversation history before answering.

Answer directly and naturally — do NOT reference page numbers or excerpt numbers in your response."""


#  Helpers 

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
    recent = [m for m in history if m.get("text", "").strip()]
    recent = recent[-settings.HISTORY_MESSAGES_LIMIT:]
    groq_messages = []
    for msg in recent:
        role = "assistant" if msg["role"] == "ai" else "user"
        groq_messages.append({"role": role, "content": msg["text"]})
    return groq_messages


def build_retrieval_query(question: str, history: List[Dict]) -> str:
    last_user_q = ""
    for msg in reversed(history):
        if msg.get("role") == "user" and msg.get("text", "").strip():
            last_user_q = msg["text"].strip()
            break
    if last_user_q and last_user_q.lower() != question.lower():
        return f"{last_user_q} {question}"
    return question


def _get_top_chunks(book_id: str, question: str, history: List[Dict] = None) -> List[Dict]:
    retrieval_query = build_retrieval_query(question, history or [])
    if retrieval_query != question:
        logger.info(f"History-aware query: '{retrieval_query[:80]}'")

    query_vector = embedding_service.embed_query(retrieval_query)
    raw_results  = vector_store.search(
        book_id=book_id,
        query_embedding=query_vector,
        top_k=settings.RERANK_CANDIDATES,
    )
    candidates = parse_raw_results(raw_results)
    if not candidates:
        return []

    return embedding_service.rerank(
        query=question,
        chunks=candidates,
        top_n=settings.TOP_K_RESULTS,
    )


def build_llm_messages(context_string: str, question: str, history_messages: List[Dict]) -> List[Dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history_messages)
    human_message = HUMAN_PROMPT_TEMPLATE.format(context=context_string, question=question)
    messages.append({"role": "user", "content": human_message})
    return messages


#  Non-streaming 

async def answer_question(
    book_id: str,
    question: str,
    history: Optional[List[Dict]] = None,
) -> QueryResponse:
    history    = history or []
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


#  Streaming 

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


#  Quiz generation 

QUIZ_PROMPT_TEMPLATE = """You are a school teacher creating a quiz based on textbook content.

Here are excerpts from the student's textbook:

{context}

---

Generate exactly {num_questions} multiple choice questions based ONLY on the content above.

STRICT FORMAT — respond with valid JSON only, no extra text:
{{
  "questions": [
    {{
      "question": "Question text here?",
      "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
      "correct": "A",
      "explanation": "Brief explanation why this is correct, based on the textbook."
    }}
  ]
}}

RULES:
- Questions must be answerable from the excerpts only
- One clearly correct answer per question
- Keep language simple for school students
- Do NOT mention page numbers or excerpt numbers in questions or explanations"""


async def generate_quiz(book_id: str, topic: str, num_questions: int = 5) -> dict:
    query_vector = embedding_service.embed_query(topic)
    raw_results  = vector_store.search(
        book_id=book_id,
        query_embedding=query_vector,
        top_k=settings.RERANK_CANDIDATES,
    )
    candidates = parse_raw_results(raw_results)

    if not candidates:
        return {"questions": [], "error": "No content found for this topic in the textbook."}

    top_chunks = embedding_service.rerank(
        query=topic, chunks=candidates, top_n=settings.TOP_K_RESULTS,
    )

    context_string = build_context_string(top_chunks)
    prompt = QUIZ_PROMPT_TEMPLATE.format(context=context_string, num_questions=num_questions)

    logger.info(f"Generating quiz | topic='{topic}' | questions={num_questions}")
    completion = sync_groq_client.chat.completions.create(
        model=settings.LLM_MODEL,
        temperature=0.3,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    try:
        result = json.loads(completion.choices[0].message.content.strip())
        logger.info(f"Quiz generated: {len(result.get('questions', []))} questions")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Quiz JSON parse error: {e}")
        return {"questions": [], "error": "Failed to generate quiz. Please try again."}