import fitz          # PyMuPDF
import re
from typing import List, Dict, Any, Tuple, Optional
from Config import settings

 
_HEADING_PATTERNS = [
    r"^(Chapter|CHAPTER|Unit|UNIT|Section|SECTION|Part|PART)\s+\w+",
    r"^\d+[\.\)]\s+[A-Z]",
    r"^\d+\.\d+\s+[A-Z]",
    r"^[A-Z][A-Z\s]{4,40}$",
    r"^[A-Z][a-z].*:$",
]
_HEADING_RE = re.compile("|".join(_HEADING_PATTERNS))


def _is_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 120:
        return False
    return bool(_HEADING_RE.match(line))

 
def _get_block_x_center(block: tuple) -> float:
    """Returns the horizontal center of a block's bounding box."""
    x0, x1 = block[0], block[2]
    return (x0 + x1) / 2


def _detect_column_split(
    blocks: List[tuple],
    page_width: float
) -> Optional[float]:
    
    page_mid = page_width / 2

    # Exclude full-width blocks from column analysis
    content_blocks = [
        b for b in blocks
        if (b[2] - b[0]) < page_width * 0.70  # not full-width
        and b[4].strip()                         # has text
    ]

    if len(content_blocks) < 4:
        # Too few blocks to determine layout reliably → assume single column
        return None

    x_centers = [_get_block_x_center(b) for b in content_blocks]

    left_centers  = [x for x in x_centers if x < page_mid * 1.1]
    right_centers = [x for x in x_centers if x > page_mid * 0.9]

    # Need meaningful presence on BOTH sides
    if len(left_centers) < 2 or len(right_centers) < 2:
        return None

    # Check for a real gap: rightmost left block vs leftmost right block
    # We use block x1 (right edge) for left blocks and x0 (left edge) for right blocks
    left_blocks  = [b for b in content_blocks if _get_block_x_center(b) < page_mid * 1.1]
    right_blocks = [b for b in content_blocks if _get_block_x_center(b) > page_mid * 0.9]

    # Max right-edge of all left-column blocks
    max_left_x1  = max(b[2] for b in left_blocks)
    # Min left-edge of all right-column blocks
    min_right_x0 = min(b[0] for b in right_blocks)

    # There must be a physical gap between the two columns
    # (gap ≥ 1% of page width — even a thin gutter qualifies)
    gap = min_right_x0 - max_left_x1
    min_gap = page_width * 0.01

    if gap < min_gap:
        # Blocks overlap horizontally → not a clean 2-column layout
        return None

    # Split point = center of the gap
    split_x = max_left_x1 + gap / 2
    return split_x


# COLUMN-AWARE BLOCK ORDERING

def _is_full_width(block: tuple, page_width: float) -> bool:
    return (block[2] - block[0]) > page_width * 0.70


def _order_blocks_by_columns(
    blocks: List[tuple],
    page_width: float,
    split_x: float
) -> List[tuple]:
    
    # Sort all blocks top-to-bottom
    sorted_blocks = sorted(blocks, key=lambda b: b[1])  # b[1] = y0

    result: List[tuple]  = []
    left_col:  List[tuple] = []
    right_col: List[tuple] = []

    def flush_columns():
        
        # Sort each column top→bottom independently
        result.extend(sorted(left_col, key=lambda b: b[1]))
        result.extend(sorted(right_col, key=lambda b: b[1]))
        left_col.clear()
        right_col.clear()

    for block in sorted_blocks:
        if not block[4].strip():
            continue  # skip empty blocks

        if _is_full_width(block, page_width):
            # Full-width block: flush any pending column blocks first
            flush_columns()
            result.append(block)
        elif _get_block_x_center(block) <= split_x:
            left_col.append(block)
        else:
            right_col.append(block)

    # Flush any remaining column blocks at end of page
    flush_columns()

    return result




def _clean_block_text(text: str) -> str:
    text = re.sub(r"-\n", "", text)          # fix hyphenated line-breaks
    text = re.sub(r"\n{3,}", "\n\n", text)   # collapse excess newlines
    text = re.sub(r" {2,}", " ", text)       # collapse spaces
    lines = [l.strip() for l in text.split("\n")]
    return "\n".join(lines).strip()


def extract_pages(file_bytes: bytes) -> List[Dict[str, Any]]:
     
    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []

    for page_num in range(len(pdf)):
        page      = pdf[page_num]
        page_rect = page.rect
        page_width  = page_rect.width
        page_height = page_rect.height  # noqa: F841 (available for future use)

        # Get blocks: (x0, y0, x1, y1, text, block_no, block_type)
        # block_type 0 = text, 1 = image — we skip images
        raw_blocks = [
            b for b in page.get_text("blocks", sort=False)
            if b[6] == 0 and b[4].strip()   # text blocks only, non-empty
        ]

        if not raw_blocks:
            continue

        #   Detect column layout 
        split_x = _detect_column_split(raw_blocks, page_width)
        layout  = "double" if split_x is not None else "single"

        #   Re-order blocks for correct reading order
        if split_x is not None:
            ordered_blocks = _order_blocks_by_columns(raw_blocks, page_width, split_x)
        else:
            # Single column: just sort top→bottom (PyMuPDF order may not be perfect)
            ordered_blocks = sorted(raw_blocks, key=lambda b: b[1])

        #   Build structured block list
        structured_blocks = []
        full_text_parts   = []

        for block in ordered_blocks:
            cleaned = _clean_block_text(block[4])
            if not cleaned:
                continue

            first_line = cleaned.split("\n")[0].strip()
            is_heading = _is_heading(first_line)

            structured_blocks.append({"text": cleaned, "is_heading": is_heading})
            full_text_parts.append(cleaned)

        if not full_text_parts:
            continue

        pages.append({
            "page_number": page_num + 1,
            "text":        "\n\n".join(full_text_parts),
            "blocks":      structured_blocks,
            "layout":      layout,
        })

        if layout == "double":
            logger.info(f"  Page {page_num + 1}: 2-column layout detected (split at x={split_x:.1f})")

    pdf.close()

    single = sum(1 for p in pages if p["layout"] == "single")
    double = sum(1 for p in pages if p["layout"] == "double")
    logger.info(f"Extraction complete: {len(pages)} pages | {single} single-column, {double} two-column")

    return pages


# SEMANTIC CHUNKING 

def _split_into_paragraphs(blocks: List[Dict]) -> List[Dict]:
    """Splits blocks into individual paragraph units."""
    paragraphs = []
    for block in blocks:
        is_heading_block = block["is_heading"]
        parts = re.split(r"\n\n+", block["text"])
        parts = [p.strip() for p in parts if p.strip()]
        for i, part in enumerate(parts):
            paragraphs.append({
                "text":       part,
                "is_heading": is_heading_block and (i == 0),
            })
    return paragraphs


def _group_paragraphs_into_chunks(
    paragraphs: List[Dict],
    page_number: int,
    max_chars: int,
) -> List[Dict]:
    chunks       = []
    current_parts: List[str] = []
    current_len  = 0
    chunk_index  = 0

    def flush():
        nonlocal chunk_index, current_parts, current_len
        text = "\n\n".join(current_parts).strip()
        if len(text) > 60:
            chunks.append({
                "text":        text,
                "page_number": page_number,
                "chunk_index": chunk_index,
                "char_start":  0,
                "char_end":    len(text),
            })
            chunk_index += 1
        current_parts = []
        current_len   = 0

    for para in paragraphs:
        para_text = para["text"]
        para_len  = len(para_text)

        if para["is_heading"] and current_parts:
            flush()

        if current_len + para_len > max_chars and current_parts:
            flush()

        current_parts.append(para_text)
        current_len += para_len

    if current_parts:
        flush()

    return chunks


def _add_overlap(chunks: List[Dict], overlap_sentences: int = 2) -> List[Dict]:
    if len(chunks) <= 1:
        return chunks

    updated = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_text      = chunks[i - 1]["text"]
        sentences      = re.split(r"(?<=[.!?])\s+", prev_text.strip())
        tail           = " ".join(sentences[-overlap_sentences:]).strip()
        new_text       = (
            f"[Context from previous section: {tail}]\n\n{chunks[i]['text']}"
            if tail else chunks[i]["text"]
        )
        updated.append({**chunks[i], "text": new_text})

    return updated


def chunk_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    all_chunks = []
    for page_data in pages:
        blocks     = page_data.get("blocks", [])
        if not blocks:
            continue
        paragraphs  = _split_into_paragraphs(blocks)
        page_chunks = _group_paragraphs_into_chunks(
            paragraphs, page_data["page_number"], settings.CHUNK_SIZE
        )
        page_chunks = _add_overlap(page_chunks)
        all_chunks.extend(page_chunks)

    for i, chunk in enumerate(all_chunks):
        chunk["chunk_index"] = i

    return all_chunks


def process_pdf(file_bytes: bytes):
    pages  = extract_pages(file_bytes)
    chunks = chunk_pages(pages)
    return chunks, len(pages)


import logging
logger = logging.getLogger(__name__)