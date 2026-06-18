from __future__ import annotations

import os
import json
from typing import Any
from pathlib import Path
from pypdf import PdfReader
import re
import arxiv
import urllib.request
import requests

def safe_filename(text: str, max_len: int = 100) -> str:
    text = re.sub(r"[^\w\s.-]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text[:max_len]


def quick_check_from_url(
    pdf_url: str,
    title: str,
    arxiv_id: str,
    output_dir: str = "papers/pdf",
) -> str:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{arxiv_id.replace('/', '_')}_{safe_filename(title)}.pdf"
    pdf_path = out_dir / filename

    req = urllib.request.Request(
        pdf_url,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        pdf_path.write_bytes(response.read())

    return str(pdf_path)


def extract_pdf_text(pdf_path: str, max_chars: int = 50_000) -> str:
    reader = PdfReader(pdf_path)
    text_parts = []

    for page_no, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""

        if page_text.strip():
            text_parts.append(f"\n\n--- Page {page_no} ---\n{page_text}")

        full_text = "\n".join(text_parts)
        if len(full_text) >= max_chars:
            return full_text[:max_chars]

    return "\n".join(text_parts)[:max_chars]

QUANT_SOURCES = [
    "arXiv q-fin.TR — Trading and Market Microstructure",
    "arXiv q-fin main archive",
    "SSRN Financial Economics Network",
    "Google Scholar",
    "NBER Asset Pricing Program",
    "Journal of Financial Economics",
    "Review of Financial Studies",
    "Journal of Finance",
    "Journal of Financial Markets",
    "Quantitative Finance Journal",
    "Journal of Computational Finance",
    "AQR Research",
    "Man Institute / Man AHL Research",
    "Two Sigma Insights",
    "Quantpedia",
]


def search_arxiv_qfin(
    scope_query: dict[str, Any],
    max_results: int = 5,
    max_pdf_downloads: int = 10,
    pdf_output_dir: str = "papers/pdf",
    max_pdf_chars: int = 50_000,
) -> list[dict[str, Any]]:
    """Search arXiv q-fin papers, optionally download PDFs, and extract text.

    Expected input:
        scope_query = {
            "queries": [
                "cat:q-fin.TR OR cat:q-fin.PM cryptocurrency momentum",
                ...
            ]
        }

    Notes:
    - Uses result.pdf_url instead of result.download_pdf(), because some arxiv
      package versions do not expose download_pdf() on Result.
    - Deduplicates by result.entry_id across multiple queries.
    - Limits PDF downloads to avoid slow runs and arXiv/API throttling.
    """
    client = arxiv.Client()
    results: list[dict[str, Any]] = []

    queries = scope_query.get("queries", []) if isinstance(scope_query, dict) else []
    if not queries:
        return results

    seen_links: set[str] = set()
    paper_no = 1
    pdf_download_count = 0

    for q in queries:
        search = arxiv.Search(
            query=q,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        for result in client.results(search):
     
            # Avoid duplicate papers returned by different queries.
            if result.entry_id in seen_links:
                continue
            seen_links.add(result.entry_id)

            arxiv_id = result.get_short_id()
            pdf_path = None
            paper_text = None
            pdf_parse_status = "not_downloaded"

            # Download and parse only the first N unique papers.
            if result.pdf_url and pdf_download_count < max_pdf_downloads:
                try:
                    pdf_path = quick_check_from_url(
                        pdf_url=result.pdf_url,
                        title=result.title,
                        arxiv_id=arxiv_id,
                        output_dir=pdf_output_dir,
                    )
                    #paper_text = extract_pdf_text(pdf_path, max_chars=max_pdf_chars)
                    #pdf_parse_status = "parsed" if paper_text else "empty_text"
                    pdf_download_count += 1

                except Exception as e:
                    pdf_parse_status = f"failed: {type(e).__name__}: {e}"
                    print(f"Failed to download or parse paper: {result.title}")
                    print("Error type:", type(e).__name__)
                    print("Error message:", str(e))

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
                    #"paper_text": paper_text,
                    "pdf_parse_status": pdf_parse_status,
                    "authors": [a.name for a in result.authors],
                    "published": str(result.published.date()) if result.published else None,
                    "categories": result.categories,
                    "source": "arXiv q-fin",
                    "query_used": q,
                }
            )

            paper_no += 1

    return results

def fallback_seed_papers(scope_query: str) -> list[dict[str, Any]]:
    """Fallback examples when online search fails.

    These are placeholders to keep the workflow runnable.
    Replace with real search results in production.
    """
    return [
        {
            "paper_id": "paper_1",
            "title": "Time Series Momentum",
            "link": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2089463",
            "brief_summary": "Studies trend-following/time-series momentum across asset classes. Often reproducible using daily futures or ETF proxy data.",
            "source": "SSRN / academic finance",
        },
        {
            "paper_id": "paper_2",
            "title": "Momentum Crashes",
            "link": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2371227",
            "brief_summary": "Studies momentum strategy risk and crash behavior. Reproduction may require equity universe data and careful portfolio construction.",
            "source": "SSRN / academic finance",
        },
        {
            "paper_id": "paper_3",
            "title": "A Century of Evidence on Trend-Following Investing",
            "link": "https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing",
            "brief_summary": "AQR paper on long-term trend-following across asset classes. Approximate reproduction possible with futures/ETF proxies.",
            "source": "AQR Research",
        },
        {
            "paper_id": "paper_4",
            "title": "Machine Learning for Asset Managers",
            "link": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3420952",
            "brief_summary": "ML methods for financial prediction and portfolio construction. Reproducibility depends heavily on available features and data.",
            "source": "SSRN",
        },
        {
            "paper_id": "paper_5",
            "title": "Pairs Trading: Performance of a Relative-Value Arbitrage Rule",
            "link": "https://academic.oup.com/rfs/article-abstract/19/3/797/1571498",
            "brief_summary": "Classic pairs trading research. Approximate reproduction possible using public equity price data, but exact universe may differ.",
            "source": "Review of Financial Studies",
        },
    ]


def search_papers(scope_query: str) -> list[dict[str, Any]]:
    try:

        papers = search_arxiv_qfin(scope_query)
        if papers:
            output_path = Path(r"C:\Users\FaiChung\Desktop\quant\ai_agent\quant_research_langchain_workflow\paper_check.json")
            with output_path.open("w", encoding="utf-8") as f:
                    json.dump(
                        papers,
                        f,
                        ensure_ascii=False,
                        indent=2,
                        default=str,   # handle datetime / unusual objects
                    )

                    print(f"Saved {len(papers)} papers to {output_path}")
            return papers
    except Exception as e:
        print("Error occurred.")
        print("Error type:", type(e).__name__)
        print("Error message:", str(e))
    return fallback_seed_papers(scope_query)


def find_free_data_sources(selected_paper: dict[str, Any]) -> list[dict[str, Any]]:
    """Suggest free data sources by paper requirement.

    In production, each source should have a real downloader/connector.
    """
    title = selected_paper.get("title", "").lower()
    sources = []

    if any(k in title for k in ["momentum", "trend", "futures"]):
        sources.extend(
            [
                {
                    "name": "Yahoo Finance ETF proxy data",
                    "type": "free",
                    "url": "https://finance.yahoo.com/",
                    "notes": "Useful for ETF proxy reproduction when continuous futures data is unavailable.",
                    "downloadable_by_agent": False,
                },
                {
                    "name": "Stooq daily price data",
                    "type": "free",
                    "url": "https://stooq.com/db/",
                    "notes": "Free historical daily data for many assets. Coverage varies.",
                    "downloadable_by_agent": False,
                },
                {
                    "name": "Nasdaq Data Link free datasets",
                    "type": "free",
                    "url": "https://data.nasdaq.com/",
                    "notes": "Some free macro/market datasets. Futures data may require paid access.",
                    "downloadable_by_agent": False,
                },
            ]
        )

    if any(k in title for k in ["crypto", "bitcoin", "order book"]):
        sources.extend(
            [
                {
                    "name": "Binance public API",
                    "type": "free",
                    "url": "https://developers.binance.com/",
                    "notes": "Free crypto OHLCV and some market data. Useful for crypto strategy reproduction.",
                    "downloadable_by_agent": True,
                },
                {
                    "name": "Kaggle crypto datasets",
                    "type": "free",
                    "url": "https://www.kaggle.com/datasets",
                    "notes": "May require manual download and Kaggle login/API token.",
                    "downloadable_by_agent": False,
                },
            ]
        )

    if not sources:
        sources.extend(
            [
                {
                    "name": "Yahoo Finance",
                    "type": "free",
                    "url": "https://finance.yahoo.com/",
                    "notes": "Good for approximate daily price reproduction.",
                    "downloadable_by_agent": False,
                },
                {
                    "name": "FRED",
                    "type": "free",
                    "url": "https://fred.stlouisfed.org/",
                    "notes": "Useful for macro factors and rates.",
                    "downloadable_by_agent": False,
                },
            ]
        )

    return sources


def paid_data_recommendations(selected_paper: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": "Nasdaq Data Link premium datasets",
            "reason": "May provide continuous futures, fundamentals, or specialized market datasets.",
        },
        {
            "name": "TickData / AlgoSeek / Polygon.io",
            "reason": "Useful when tick, intraday, order book, or survivorship-bias-free data is required.",
        },
        {
            "name": "Bloomberg / Refinitiv",
            "reason": "Institutional source for broad asset coverage and reliable historical data.",
        },
    ]


def ensure_output_dir() -> Path:
    out = Path("notebooks/output")
    out.mkdir(parents=True, exist_ok=True)
    return out


def get_arxiv_id_from_link(link: str) -> str:
    """
    Extract arXiv ID from links like:
    http://arxiv.org/abs/2112.09807v1
    https://arxiv.org/pdf/2112.09807v1.pdf
    http://arxiv.org/abs/hep-ex/0505100v1
    """
    match = re.search(r"arxiv\.org/(?:abs|pdf)/(.+)", link)

    if not match:
        return ""

    arxiv_id = match.group(1)
    arxiv_id = arxiv_id.split("?")[0]
    arxiv_id = arxiv_id.replace(".pdf", "")

    return arxiv_id


def get_arxiv_pdf_url(link: str) -> str:
    """
    Convert arXiv abstract link to PDF link.
    """
    arxiv_id = get_arxiv_id_from_link(link)

    if not arxiv_id:
        raise ValueError(f"Cannot extract arXiv ID from link: {link}")

    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"


def safe_filename(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", text)


def download_pdf_from_url(pdf_url: str, output_dir: str = "data/papers") -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    arxiv_id = get_arxiv_id_from_link(pdf_url)
    filename = safe_filename(arxiv_id) + ".pdf"

    pdf_path = output_path / filename

    headers = {
        "User-Agent": "quant-research-agent/0.1"
    }

    response = requests.get(pdf_url, headers=headers, timeout=30)
    response.raise_for_status()

    if len(response.content) < 1000:
        raise ValueError(f"Downloaded file seems too small: {pdf_url}")

    pdf_path.write_bytes(response.content)

    return pdf_path


def extract_text_from_pdf(pdf_path: Path, max_chars: int = 60000) -> str:
    reader = PdfReader(str(pdf_path))

    pages_text = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)

        if sum(len(t) for t in pages_text) >= max_chars:
            break

    full_text = "\n\n".join(pages_text)

    return full_text[:max_chars]