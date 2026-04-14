
import fitz  # PyMuPDF — fitz is the internal name
import re
from typing import List, Dict, Any
from Config import settings


def extract_text_from_pdf(file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Opens a PDF from raw bytes and extracts clean text page by page.

    Returns a list of dicts, one per page:
        [
            {"page_number": 1, "text": "Chapter 1 Introduction..."},
            {"page_number": 2, "text": "Photosynthesis is the process..."},
            ...
        ]

    Args:
        file_bytes: Raw bytes of the uploaded PDF file

    Returns:
        List of page dicts with page_number and text
    """
    pages = []

    # Open PDF from memory (no need to save to disk)
    pdf_document = fitz.open(stream=file_bytes, filetype="pdf")

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]

        # get_text("text") extracts plain text, preserving line breaks
        raw_text = page.get_text("text")

        # Clean the text: collapse multiple spaces/newlines into single ones
        cleaned_text = clean_text(raw_text)

        # Skip pages that are blank or nearly blank (images, decorative pages)
        if len(cleaned_text.strip()) < 50:
            continue

        pages.append({
            "page_number": page_num + 1,  # Human-readable (1-indexed)
            "text": cleaned_text
        })

    pdf_document.close()
    return pages


def clean_text(text: str) -> str:
    """
    Cleans raw PDF text by removing noise introduced by PDF extraction.

    Common PDF extraction issues:
    - Multiple consecutive newlines (whitespace blobs)
    - Hyphenated words split across lines ("photo-\nsynthesis")
    - Trailing/leading whitespace per line
    """
    # Re-join hyphenated words that were split at end of line
    text = re.sub(r"-\n", "", text)

    # Collapse 3+ newlines into a double newline (paragraph break)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse multiple spaces into one
    text = re.sub(r" {2,}", " ", text)

    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()


def chunk_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Splits each page's text into overlapping chunks.

    ALGORITHM:
    - For each page, slide a window of CHUNK_SIZE characters
    - Move the window forward by (CHUNK_SIZE - CHUNK_OVERLAP) each step
    - This means consecutive chunks share CHUNK_OVERLAP characters

    Example with CHUNK_SIZE=800, CHUNK_OVERLAP=150:
        Chunk 0: chars   0 → 800
        Chunk 1: chars 650 → 1450   ← shares 150 chars with chunk 0
        Chunk 2: chars 1300 → 2100  ← shares 150 chars with chunk 1

    Each chunk gets metadata (page_number, chunk_index) so we can
    show the student exactly where in the book the answer came from.

    Returns:
        List of chunk dicts:
        [
            {
                "text": "Photosynthesis is...",
                "page_number": 3,
                "chunk_index": 0,
                "char_start": 0,
                "char_end": 800
            },
            ...
        ]
    """
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
    """
    Full pipeline: bytes → pages → chunks.

    Returns:
        (chunks, total_pages)
    """
    pages = extract_text_from_pdf(file_bytes)
    chunks = chunk_pages(pages)
    return chunks, len(pages)