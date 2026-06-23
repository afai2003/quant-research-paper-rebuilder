from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import arxiv
import requests
from pypdf import PdfReader


QUANT_SOURCES = [
    "arXiv q-fin.TR — Trading and Market Microstructure",
    "arXiv q-fin.PM — Portfolio Management",
    "arXiv q-fin.ST — Statistical Finance",
    "SSRN Financial Economics Network",
    "Google Scholar",
    "NBER Asset Pricing Program",
    "Journal of Finance",
    "Journal of Financial Economics",
    "Review of Financial Studies",
    "AQR Research",
    "Man Institute / Man AHL Research",
    "Two Sigma Insights",
    "Quantpedia",
]


def safe_filename(text: str, max_len: int = 120) -> str:
    """Return a filesystem-safe filename fragment."""
    text = re.sub(r"[^a-zA-Z0-9_.-]+", "_", text.strip())
    text = text.strip("._")
    return (text or "file")[:max_len]


def quick_check_from_url(
    pdf_url: str,
    title: str,
    arxiv_id: str,
    output_dir: str = "papers/pdf",
) -> str:
    """Download an arXiv PDF to a local folder."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{safe_filename(arxiv_id)}_{safe_filename(title, max_len=80)}.pdf"
    pdf_path = out_dir / filename

    headers = {"User-Agent": "quant-research-agent/0.1"}
    response = requests.get(pdf_url, headers=headers, timeout=30)
    response.raise_for_status()

    if len(response.content) < 1000:
        raise ValueError(f"Downloaded file seems too small: {pdf_url}")

    pdf_path.write_bytes(response.content)
    return str(pdf_path)


def extract_text_from_pdf(pdf_path: str | Path, max_chars: int = 250_000) -> str:
    """Extract text from a PDF with a max character cap."""
    reader = PdfReader(str(pdf_path))
    pages_text: list[str] = []

    for page_no, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""

        if text.strip():
            pages_text.append(f"\n\n--- Page {page_no} ---\n{text}")

        if sum(len(t) for t in pages_text) >= max_chars:
            break

    return "\n".join(pages_text)[:max_chars]


# Backward-compatible alias.
extract_pdf_text = extract_text_from_pdf


def search_arxiv_qfin(
    scope_query: dict[str, Any],
    max_results: int = 5,
    max_pdf_downloads: int = 10,
    pdf_output_dir: str = "papers/pdf",
) -> list[dict[str, Any]]:
    """Search arXiv q-fin papers and download a limited number of PDFs."""
    queries = scope_query.get("queries", []) if isinstance(scope_query, dict) else []
    if not queries:
        return []

    client = arxiv.Client()
    results: list[dict[str, Any]] = []
    seen_links: set[str] = set()
    paper_no = 1
    pdf_download_count = 0

    for query in queries:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        for result in client.results(search):
            if result.entry_id in seen_links:
                continue
            seen_links.add(result.entry_id)

            arxiv_id = result.get_short_id()
            pdf_path = None
            pdf_parse_status = "not_downloaded"

            if result.pdf_url and pdf_download_count < max_pdf_downloads:
                try:
                    pdf_path = quick_check_from_url(
                        pdf_url=result.pdf_url,
                        title=result.title,
                        arxiv_id=arxiv_id,
                        output_dir=pdf_output_dir,
                    )
                    pdf_download_count += 1
                    pdf_parse_status = "downloaded"
                except Exception as exc:
                    pdf_parse_status = f"failed: {type(exc).__name__}: {exc}"
            elif not result.pdf_url:
                pdf_parse_status = "no_pdf_url"
            else:
                pdf_parse_status = "skipped_pdf_download_limit"

            results.append(
                {
                    "paper_id": f"arxiv_{paper_no}",
                    "title": result.title,
                    "arxiv_id": arxiv_id,
                    "link": result.entry_id,
                    "pdf_url": result.pdf_url,
                    "pdf_path": pdf_path,
                    "brief_summary": result.summary,
                    "pdf_parse_status": pdf_parse_status,
                    "authors": [author.name for author in result.authors],
                    "published_date": str(result.published.date()) if result.published else None,
                    "arxiv_categories": result.categories,
                    "source": "arXiv q-fin",
                    "query_used": query,
                }
            )
            paper_no += 1

    return results




def search_papers(scope_query: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Search papers and persist a debug copy under outputs/.

    If arXiv search fails, stop the workflow instead of using fallback papers.
    This avoids rebuilding an unrelated paper.
    """
    try:
        papers = search_arxiv_qfin(scope_query)

        if not papers:
            raise RuntimeError("No papers were found from arXiv for the generated queries.")

        output_path = Path("outputs/paper_search/paper_check.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(papers, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        print(f"Saved {len(papers)} papers to {output_path}")
        return papers

    except Exception as exc:
        raise RuntimeError(
            f"Paper search failed. Workflow stopped. "
            f"Error type: {type(exc).__name__}. Error message: {exc}"
        ) from exc



def get_arxiv_id_from_link(link: str) -> str:
    """Extract an arXiv ID from an abstract or PDF URL."""
    match = re.search(r"arxiv\.org/(?:abs|pdf)/(.+)", link)
    if not match:
        return ""

    arxiv_id = match.group(1).split("?")[0]
    return arxiv_id.replace(".pdf", "")


def get_arxiv_pdf_url(link: str) -> str:
    arxiv_id = get_arxiv_id_from_link(link)
    if not arxiv_id:
        raise ValueError(f"Cannot extract arXiv ID from link: {link}")
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"


def download_pdf_from_url(pdf_url: str, output_dir: str = "data/papers") -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    arxiv_id = get_arxiv_id_from_link(pdf_url) or safe_filename(Path(pdf_url).stem)
    pdf_path = output_path / f"{safe_filename(arxiv_id)}.pdf"

    headers = {"User-Agent": "quant-research-agent/0.1"}
    response = requests.get(pdf_url, headers=headers, timeout=30)
    response.raise_for_status()

    if len(response.content) < 1000:
        raise ValueError(f"Downloaded file seems too small: {pdf_url}")

    pdf_path.write_bytes(response.content)
    return pdf_path
