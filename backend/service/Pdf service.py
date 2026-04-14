
import fitz  # PyMuPDF — fitz is the internal name
import re
from typing import List, Dict, Any
from Config import settings


def extract_text_from_pdf(file_bytes: bytes) -> List[Dict[str, Any]]: # reads the rawBytes 
    
    pages = []    
    pdf_document = fitz.open(stream=file_bytes, filetype="pdf")

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        
        raw_text = page.get_text("text")    
        cleaned_text = clean_text(raw_text)
        
        if len(cleaned_text.strip()) < 50:
            continue

        pages.append({
            "page_number": page_num + 1, 
            "text": cleaned_text
        })

    pdf_document.close()
    return pages


def clean_text(text: str) -> str:
    
    text = re.sub(r"-\n", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)

    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()


def chunk_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    
    chunks = []
    chunk_size = settings.CHUNK_SIZE
    chunk_overlap = settings.CHUNK_OVERLAP
    step = chunk_size - chunk_overlap  # How far the window slides each time

    for page_data in pages:
        page_text = page_data["text"]
        page_number = page_data["page_number"]

        # If the entire page fits in one chunk, no splitting needed
        if len(page_text) <= chunk_size:
            chunks.append({
                "text": page_text,
                "page_number": page_number,
                "chunk_index": 0,
                "char_start": 0,
                "char_end": len(page_text)
            })
            continue

        # Sliding window chunking
        chunk_index = 0
        start = 0

        while start < len(page_text):
            end = start + chunk_size

            # Try to break at a sentence boundary (". ") instead of mid-word
            if end < len(page_text):
                # Look for the last period within the last 100 chars of the chunk
                last_period = page_text.rfind(". ", end - 100, end)
                if last_period != -1:
                    end = last_period + 1  # Include the period

            chunk_text = page_text[start:end].strip()

            # Only add non-trivial chunks
            if len(chunk_text) > 50:
                chunks.append({
                    "text": chunk_text,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "char_start": start,
                    "char_end": end
                })
                chunk_index += 1

            # If we already reached the end, stop
            if end >= len(page_text):
                break

            start += step  # Slide the window forward

    return chunks


def process_pdf(file_bytes: bytes) -> tuple[List[Dict], int]:
    # Full pipeline: bytes → pages → chunks.
    # Returns:    (chunks, total_pages)    
    pages = extract_text_from_pdf(file_bytes)
    chunks = chunk_pages(pages)
    return chunks, len(pages)