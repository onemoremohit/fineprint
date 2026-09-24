"""
FinePrint — Document Text Extraction

Handles PDF, DOCX, and image files.
Outputs full_text and a page map [(page_no, start, end)].
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


async def extract_text(
    content: bytes, extension: str
) -> Tuple[str, list[Tuple[int, int, int]]]:
    """
    Extract text from a document.

    Args:
        content: Raw file bytes
        extension: File extension (e.g. ".pdf", ".docx", ".jpg")

    Returns:
        (full_text, page_map) where page_map is [(page_no, start_offset, end_offset)]
    """
    ext = extension.lower()

    if ext == ".pdf":
        return _extract_pdf(content)
    elif ext in (".docx", ".doc"):
        return _extract_docx(content)
    elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
        return await _extract_image(content, ext)
    elif ext in (".txt", ".text"):
        return _extract_txt(content)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _extract_pdf(content: bytes) -> Tuple[str, list[Tuple[int, int, int]]]:
    """Extract text from PDF using PyMuPDF (fitz)."""
    import fitz

    doc = fitz.open(stream=content, filetype="pdf")
    full_text = ""
    page_map = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        page_text = page.get_text("text")

        if not page_text.strip():
            # Page might be scanned — try OCR
            logger.info(f"Page {page_num} has no text, attempting OCR...")
            try:
                from ingest.ocr import ocr_page_image
                # Render page as image
                pix = page.get_pixmap(dpi=300)
                img_bytes = pix.tobytes("png")
                page_text = ocr_page_image(img_bytes)
            except Exception as e:
                logger.warning(f"OCR failed for page {page_num}: {e}")
                page_text = ""

        start = len(full_text)
        full_text += page_text
        if not page_text.endswith("\n"):
            full_text += "\n"
        end = len(full_text)

        page_map.append((page_num, start, end))

    doc.close()
    return full_text, page_map


def _extract_docx(content: bytes) -> Tuple[str, list[Tuple[int, int, int]]]:
    """Extract text from DOCX using python-docx."""
    import io
    from docx import Document

    doc = Document(io.BytesIO(content))
    full_text = ""
    page_map = []

    # DOCX doesn't have true page boundaries, so we treat it as one page
    # but break at every ~3000 chars for approximate page mapping
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)

    page_num = 0
    page_start = 0
    chars_on_page = 0

    for para_text in paragraphs:
        start = len(full_text)
        full_text += para_text + "\n\n"
        chars_on_page += len(para_text) + 2

        # Approximate page break every 3000 chars
        if chars_on_page > 3000:
            page_map.append((page_num, page_start, len(full_text)))
            page_num += 1
            page_start = len(full_text)
            chars_on_page = 0

    # Add the last page
    if page_start < len(full_text):
        page_map.append((page_num, page_start, len(full_text)))

    # Ensure we have at least one page
    if not page_map:
        page_map = [(0, 0, len(full_text))]

    return full_text, page_map


async def _extract_image(
    content: bytes, ext: str
) -> Tuple[str, list[Tuple[int, int, int]]]:
    """Extract text from image via OCR pipeline."""
    from ingest.ocr import ocr_image

    full_text = ocr_image(content)
    page_map = [(0, 0, len(full_text))]
    return full_text, page_map


def _extract_txt(content: bytes) -> Tuple[str, list[Tuple[int, int, int]]]:
    """Extract text from plain text file."""
    text = content.decode("utf-8", errors="replace")
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    page_map = [(0, 0, len(text))]
    return text, page_map

