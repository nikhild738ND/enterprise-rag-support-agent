from __future__ import annotations

import hashlib
import re
from pathlib import Path

import markdown as md_lib
from bs4 import BeautifulSoup
from pypdf import PdfReader


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _extract_metadata(text: str, fallback_stem: str) -> tuple[str, str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    doc_id = None
    title = None
    start_index = 0
    for idx, line in enumerate(lines[:5]):
        if line.startswith("DOC_ID:"):
            doc_id = line.split(":", 1)[1].strip()
            start_index = max(start_index, idx + 1)
        elif line.startswith("TITLE:"):
            title = line.split(":", 1)[1].strip()
            start_index = max(start_index, idx + 1)
    if not doc_id:
        doc_id = f"DOC-{fallback_stem.upper().replace('_', '-')}"
    if not title:
        title = fallback_stem.replace("_", " ").replace("-", " ").title()
    cleaned_lines = lines[start_index:] if start_index else lines
    body = "\n".join(cleaned_lines)
    return doc_id, title, body


def _parse_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def _parse_html(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text("\n")


def _parse_markdown(text: str) -> str:
    html = md_lib.markdown(text)
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n")


def parse_document(path_str: str) -> dict[str, str]:
    path = Path(path_str)
    suffix = path.suffix.lower()
    raw_text = path.read_text(encoding="utf-8") if suffix not in {".pdf"} else _parse_pdf(path)

    if suffix in {".html", ".htm"}:
        raw_text = _parse_html(raw_text)
    elif suffix in {".md", ".markdown"}:
        raw_text = _parse_markdown(raw_text)

    text = _clean_text(raw_text)
    doc_id, title, body = _extract_metadata(text, path.stem)
    content_hash = hashlib.sha1(body.encode("utf-8")).hexdigest()
    return {
        "doc_id": doc_id,
        "title": title,
        "source_type": suffix.lstrip(".") or "txt",
        "source_path": str(path.resolve()),
        "content_hash": content_hash,
        "text": body,
    }
