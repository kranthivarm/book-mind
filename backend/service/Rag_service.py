from groq import Groq
from typing import List, Dict, Any
from Config import settings
from service.Embedding_service import embedding_service
from service.Vector_store import vector_store
from models.schemas import QueryResponse, SourceChunk
import logging

logger = logging.getLogger(__name__)


groq_client = Groq(api_key=settings.GROQ_API_KEY)

# prompt
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


def build_context_string(retrieved_chunks: List[Dict]) -> str: #chuncks to readable contextStr 
    
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks):
        page = chunk["metadata"]["page_number"]
        text = chunk["text"]
        context_parts.append(f"[Page {page}, Excerpt {i+1}]\n{text}")

    return "\n\n".join(context_parts)


def parse_retrieved_results(raw_results: Dict) -> List[Dict]:#db results to more cleaner list of dicts;
   
    documents = raw_results["documents"][0]
    metadatas = raw_results["metadatas"][0]
    distances = raw_results["distances"][0]

    chunks = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        chunks.append({
            "text": doc,
            "metadata": meta,
            "distance": dist
        })

    return chunks


def distance_to_score(distance: float) -> float:
    # ChromaDB returns cosine DISTANCE (0 = identical, 2 = opposite).
    # We convert to a similarity SCORE (1 = identical, 0 = irrelevant).
    # Score = 1 - (distance / 2), clamped to [0, 1].
    score = 1.0 - (distance / 2.0)
    return round(max(0.0, min(1.0, score)), 3)


async def answer_question(book_id: str, question: str) -> QueryResponse:
    

    # Embed the question
    logger.info(f"Embedding question for book_id={book_id}")
    query_vector = embedding_service.embed_query(question)

    #Retrieve relevant chunks 
    logger.info("Searching vector store for relevant chunks")
    raw_results = vector_store.search(
        book_id=book_id,
        query_embedding=query_vector
    )

    # Parse ChromaDB's nested format into flat list
    retrieved_chunks = parse_retrieved_results(raw_results)

    if not retrieved_chunks:
        # Edge case: book exists but somehow empty
        return QueryResponse(
            answer="No relevant content found in the textbook for your question.",
            sources=[],
            question=question
        )

    #prompt context-    Format chunks into a readable block for the LLM
    context_string = build_context_string(retrieved_chunks)
    human_message = HUMAN_PROMPT_TEMPLATE.format(
        context=context_string,
        question=question
    )



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




    sources = []
    for chunk in retrieved_chunks:
        sources.append(SourceChunk(
            page_number=chunk["metadata"]["page_number"],
            chunk_index=chunk["metadata"]["chunk_index"],
            text_preview=chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
            relevance_score=distance_to_score(chunk["distance"])
        ))

    return QueryResponse(
        answer=answer_text,
        sources=sources,
        question=question
    )