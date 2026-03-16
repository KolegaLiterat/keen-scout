"""
Utilities for the /researcher skill.
Manages query folders, exports, and memory.
"""

import re
import sys
import os
from datetime import datetime
from pathlib import Path

QUERIES_DIR = Path(__file__).parent / "queries"
QUERIES_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Query folder management
# ---------------------------------------------------------------------------

def make_slug(title: str) -> str:
    """Convert a short title (3–5 words) into a folder name slug."""
    date = datetime.now().strftime("%Y-%m-%d")
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = slug[:50].rstrip("-")
    return f"{date}_{slug}"


def create_query_folder(title: str) -> tuple[Path, str]:
    """
    Create a folder for a query based on a short title (3–5 words).

    Args:
        title: Short topic title, e.g. "air-quality-trends-2024"

    Returns:
        (path, slug)
    """
    slug = make_slug(title)
    folder = QUERIES_DIR / slug
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "img").mkdir(exist_ok=True)
    return folder, slug


def save_answer(slug: str, answer_md: str, sources_md: str) -> dict[str, Path]:
    """
    Save answer.md and sources.md to the query folder.

    Returns:
        Dict with paths to the files
    """
    folder = QUERIES_DIR / slug
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "img").mkdir(exist_ok=True)

    answer_path = folder / "answer.md"
    sources_path = folder / "sources.md"

    answer_path.write_text(answer_md, encoding="utf-8")
    sources_path.write_text(sources_md, encoding="utf-8")

    return {"answer": answer_path, "sources": sources_path}


def load_answer(slug: str) -> dict | None:
    """Load a saved query. Returns None if it does not exist."""
    folder = QUERIES_DIR / slug
    answer_path = folder / "answer.md"
    sources_path = folder / "sources.md"

    if not answer_path.exists():
        return None

    return {
        "answer": answer_path.read_text(encoding="utf-8"),
        "sources": sources_path.read_text(encoding="utf-8") if sources_path.exists() else "",
        "folder": folder,
    }


def list_queries() -> list[dict]:
    """List all saved queries."""
    results = []
    for folder in sorted(QUERIES_DIR.iterdir(), reverse=True):
        if folder.is_dir():
            answer_path = folder / "answer.md"
            if answer_path.exists():
                results.append({
                    "slug": folder.name,
                    "folder": folder,
                    "modified": datetime.fromtimestamp(answer_path.stat().st_mtime).isoformat(),
                })
    return results


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_docx(slug: str) -> Path:
    """
    Export answer.md to DOCX via pandoc.

    Returns:
        Path to the generated DOCX file
    """
    import pypandoc

    folder = QUERIES_DIR / slug
    answer_path = folder / "answer.md"
    docx_path = folder / "answer.docx"

    if not answer_path.exists():
        raise FileNotFoundError(f"answer.md not found in {folder}")

    pypandoc.convert_file(
        str(answer_path),
        "docx",
        outputfile=str(docx_path),
        extra_args=["--standalone"],
    )
    return docx_path


def export_pdf(slug: str) -> Path:
    """
    Export answer.md to PDF via pandoc.

    Returns:
        Path to the generated PDF file
    """
    import pypandoc

    folder = QUERIES_DIR / slug
    answer_path = folder / "answer.md"
    pdf_path = folder / "answer.pdf"

    if not answer_path.exists():
        raise FileNotFoundError(f"answer.md not found in {folder}")

    pypandoc.convert_file(
        str(answer_path),
        "pdf",
        outputfile=str(pdf_path),
        extra_args=["--pdf-engine=xelatex", "-V", "geometry:margin=2.5cm"],
    )
    return pdf_path


# ---------------------------------------------------------------------------
# Memory integration helpers
# ---------------------------------------------------------------------------

def save_to_memory(query: str, answer: str, sources: list[str], slug: str) -> str:
    """Save a research result to Chroma (memory.py)."""
    sys.path.insert(0, str(Path(__file__).parent))
    from tools.memory import save

    doc_id = save(
        query=query,
        result=answer,
        sources=sources,
        metadata={"slug": slug},
    )
    return doc_id


def search_memory(query: str, min_similarity: float = 0.65) -> list[dict]:
    """Search for similar previous research in Chroma."""
    sys.path.insert(0, str(Path(__file__).parent))
    from tools.memory import search

    return search(query, n_results=3, min_similarity=min_similarity)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cli_list():
    """researcher-list — display saved research."""
    queries = list_queries()
    if not queries:
        print("No saved research found.")
        return
    for q in queries:
        print(f"{q['slug']}  ({q['modified']})")


def cli_export():
    """researcher-export <slug> [--docx] [--pdf] — export research."""
    import argparse
    parser = argparse.ArgumentParser(description="Export saved research to DOCX or PDF")
    parser.add_argument("slug", help="Research slug (from researcher-list)")
    parser.add_argument("--docx", action="store_true")
    parser.add_argument("--pdf", action="store_true")
    args = parser.parse_args()

    if not args.docx and not args.pdf:
        parser.error("Specify --docx and/or --pdf")

    if args.docx:
        path = export_docx(args.slug)
        print(f"DOCX: {path}")

    if args.pdf:
        try:
            path = export_pdf(args.slug)
            print(f"PDF: {path}")
        except Exception as e:
            print(f"PDF unavailable: {e}. Install: brew install basictex")


if __name__ == "__main__":
    cli_list()
