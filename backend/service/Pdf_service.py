
import fitz  # PyMuPDF : fitz is the internal name
import re
from typing import List, Dict, Any, Optional
from Config import settings



# extracting pages and headings detections
_HEADING_PATTERNS = [
    r"^(Chapter|CHAPTER|Unit|UNIT|Section|SECTION|Part|PART)\s+\w+",  
    r"^\d+[\.\)]\s+[A-Z]",           # 1. Introduction  /  1) Overview
    r"^\d+\.\d+\s+[A-Z]",            # 1.2 Subsection
    r"^[A-Z][A-Z\s]{4,40}$",         # ALL CAPS SHORT LINE  (e.g. INTRODUCTION)
    r"^[A-Z][a-z].*:$",              # Title case ending with colon
]
_HEADING_RE = re.compile("|".join(_HEADING_PATTERNS))
 
 
def _is_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 120:  
        return False
    return bool(_HEADING_RE.match(line))


def extract_pages(file_bytes: bytes) -> List[Dict[str, Any]]:
   
    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
 
    for page_num in range(len(pdf)):
        page = pdf[page_num]
 
        # get_text("blocks") gives us text grouped by visual block (paragraph-like)
        # Each block: (x0, y0, x1, y1, text, block_no, block_type)
        raw_blocks = page.get_text("blocks", sort=True)  # sort=True → reading order
 
        blocks = []
        full_text_parts = []
 
        for block in raw_blocks:
            block_text = block[4].strip()
            if not block_text or len(block_text) < 5:
                continue
 
            cleaned = _clean_block(block_text)
            if not cleaned:
                continue
 
            # Check if the first line of the block is a heading
            first_line = cleaned.split("\n")[0].strip()
            is_heading = _is_heading(first_line)
 
            blocks.append({"text": cleaned, "is_heading": is_heading})
            full_text_parts.append(cleaned)
 
        if not full_text_parts:#blank pages
            continue  
 
        pages.append({
            "page_number": page_num + 1,
            "text": "\n\n".join(full_text_parts),
            "blocks": blocks,
        })
 
    pdf.close()
    return pages
 
 
def _clean_block(text: str) -> str:  #cleaning text block     


    text = re.sub(r"-\n", "", text)  # line ending - 

    text = re.sub(r"\n{3,}", "\n\n", text)

    text = re.sub(r" {2,}", " ", text)

    lines = [l.strip() for l in text.split("\n")]
    return "\n".join(lines).strip()
 


#split into paragraphs

def _split_into_paragraphs(blocks: List[Dict]) -> List[Dict]:
   
    paragraphs = []
 
    for block in blocks:
        raw = block["text"]
        is_heading_block = block["is_heading"]
 
        parts = re.split(r"\n\n+", raw)
        parts = [p.strip() for p in parts if p.strip()]
 
        for i, part in enumerate(parts):
            # Only the first part of a heading block gets the heading flag
            is_heading = is_heading_block and (i == 0)
            paragraphs.append({
                "text": part,
                "is_heading": is_heading,
            })
 
    return paragraphs


#Group paragraphs into semantic chunks
def _group_paragraphs_into_chunks(
    paragraphs: List[Dict],
    page_number: int,
    max_chars: int,
) -> List[Dict]:
    

    chunks = []
    current_parts = []
    current_len = 0
    chunk_index = 0
 
    def flush(extra_paragraph: Optional[str] = None):
        """Save current_parts as a chunk, then reset."""
        nonlocal chunk_index, current_parts, current_len
 
        parts_to_flush = current_parts[:]
        if extra_paragraph:
            parts_to_flush.append(extra_paragraph)
 
        text = "\n\n".join(parts_to_flush).strip()
        if len(text) > 60:  # skip trivially small chunks
            chunks.append({
                "text": text,
                "page_number": page_number,
                "chunk_index": chunk_index,
                "char_start": 0,   # approximate; not critical after reranking
                "char_end": len(text),
            })
            chunk_index += 1
 
        current_parts = []
        current_len = 0
 
    for i, para in enumerate(paragraphs):
        para_text = para["text"]
        para_len = len(para_text)
 
        if para["is_heading"] and current_parts:
            flush()

            current_parts = [para_text]
            current_len = para_len
            continue
 
        if current_len + para_len > max_chars and current_parts:
            flush()
 
        current_parts.append(para_text)
        current_len += para_len
 
    if current_parts:
        flush()
 
    return chunks
 

# Add contextual overlap between chunks

def _add_overlap(chunks: List[Dict], overlap_sentences: int = 2) -> List[Dict]:
     
    if len(chunks) <= 1:
        return chunks
 
    updated = [chunks[0]]  # first chunk has no previous
 
    for i in range(1, len(chunks)):
        prev_text = chunks[i - 1]["text"]
 
        # Extract last N sentences from previous chunk
        sentences = re.split(r"(?<=[.!?])\s+", prev_text.strip())
        tail_sentences = sentences[-overlap_sentences:]
        overlap_text = " ".join(tail_sentences).strip()
 
        if overlap_text:
            # Prefix with a clear marker so LLM knows this is bridging context
            new_text = f"[Context from previous section: {overlap_text}]\n\n{chunks[i]['text']}"
        else:
            new_text = chunks[i]["text"]
 
        updated.append({**chunks[i], "text": new_text})
 
    return updated
 


def chunk_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    
    all_chunks = []
 
    for page_data in pages:
        blocks = page_data.get("blocks", [])
        if not blocks:
            continue
 
        paragraphs = _split_into_paragraphs(blocks)
 
        page_chunks = _group_paragraphs_into_chunks(
            paragraphs=paragraphs,
            page_number=page_data["page_number"],
            max_chars=settings.CHUNK_SIZE,
        )
 
        page_chunks = _add_overlap(page_chunks, overlap_sentences=2)
 
        all_chunks.extend(page_chunks)
 
    # Re-index chunk_index globally (was per-page)
    for i, chunk in enumerate(all_chunks):
        chunk["chunk_index"] = i
 
    return all_chunks
 
 
def process_pdf(file_bytes: bytes):   
    pages = extract_pages(file_bytes)
    chunks = chunk_pages(pages)
    return chunks, len(pages)
 



# def extract_text_from_pdf(file_bytes: bytes) -> List[Dict[str, Any]]: # reads the rawBytes 
    
#     pages = []    
#     pdf_document = fitz.open(stream=file_bytes, filetype="pdf")

#     for page_num in range(len(pdf_document)):
#         page = pdf_document[page_num]
        
#         raw_text = page.get_text("text")    
#         cleaned_text = clean_text(raw_text)
        
#         if len(cleaned_text.strip()) < 50:
#             continue

#         pages.append({
#             "page_number": page_num + 1, 
#             "text": cleaned_text
#         })

#     pdf_document.close()
#     return pages


# def clean_text(text: str) -> str:
    
#     text = re.sub(r"-\n", "", text)
#     text = re.sub(r"\n{3,}", "\n\n", text)
#     text = re.sub(r" {2,}", " ", text)

#     lines = [line.strip() for line in text.split("\n")]
#     text = "\n".join(lines)

#     return text.strip()


# def chunk_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    
#     chunks = []
#     chunk_size = settings.CHUNK_SIZE
#     chunk_overlap = settings.CHUNK_OVERLAP
#     step = chunk_size - chunk_overlap  # How far the window slides each time

#     for page_data in pages:
#         page_text = page_data["text"]
#         page_number = page_data["page_number"]

#         # If the entire page fits in one chunk, no splitting needed
#         if len(page_text) <= chunk_size:
#             chunks.append({
#                 "text": page_text,
#                 "page_number": page_number,
#                 "chunk_index": 0,
#                 "char_start": 0,
#                 "char_end": len(page_text)
#             })
#             continue

#         # Sliding window chunking
#         chunk_index = 0
#         start = 0

#         while start < len(page_text):
#             end = start + chunk_size

#             # Try to break at a sentence boundary (". ") instead of mid-word
#             if end < len(page_text):
#                 # Look for the last period within the last 100 chars of the chunk
#                 last_period = page_text.rfind(". ", end - 100, end)
#                 if last_period != -1:
#                     end = last_period + 1  # Include the period

#             chunk_text = page_text[start:end].strip()

#             # Only add non-trivial chunks
#             if len(chunk_text) > 50:
#                 chunks.append({
#                     "text": chunk_text,
#                     "page_number": page_number,
#                     "chunk_index": chunk_index,
#                     "char_start": start,
#                     "char_end": end
#                 })
#                 chunk_index += 1

#             # If we already reached the end, stop
#             if end >= len(page_text):
#                 break

#             start += step  # Slide the window forward

#     return chunks


# def process_pdf(file_bytes: bytes) -> tuple[List[Dict], int]:
#     # Full pipeline: bytes → pages → chunks.
#     # Returns:    (chunks, total_pages)    
#     pages = extract_text_from_pdf(file_bytes)
#     chunks = chunk_pages(pages)
#     return chunks, len(pages)