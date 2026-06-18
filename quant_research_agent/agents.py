from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from .llm import get_llm
from .notebook_writer import jupyter_code_to_notebook
from .prompts import (
    ARXIV_QUERY_DECOMPOSER_PROMPT,
    BA_PROMPT,
    PAPER_READING_PROMPT,
    QR_PAPER_PROMPT,
    QUANT_RESEARCHER_WRITE_NOTEBOOK_PROMPT,
    REVIEWER_PROMPT,
)
from .tools import (
    download_pdf_from_url,
    extract_text_from_pdf,
    find_free_data_sources,
    get_arxiv_pdf_url,
    paid_data_recommendations,
    search_papers,
)


def strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text.removeprefix("```json").strip()
    elif text.startswith("```python"):
        text = text.removeprefix("```python").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").strip()
    if text.endswith("```"):
        text = text.removesuffix("```").strip()
    return text


def extract_json_object(text: str) -> str:
    """Extract the first JSON object from a model response."""
    text = strip_markdown_fence(text)
    if text.startswith("{") and text.endswith("}"):
        return text

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        return match.group(0)
    return text


def safe_json_from_llm(
    system_prompt: str,
    user_content: str,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    """Ask the LLM for JSON; return fallback if parsing fails."""
    llm = get_llm(temperature=0.1)
    response = llm.invoke(
        [
            SystemMessage(content=f"{system_prompt.strip()}\nReturn valid JSON only. No markdown."),
            HumanMessage(content=user_content),
        ]
    )
    text = response.content if isinstance(response.content, str) else str(response.content)

    try:
        return json.loads(extract_json_object(text))
    except Exception as exc:
        print("JSON parsing failed; using fallback.")
        print("Error type:", type(exc).__name__)
        print("Error message:", str(exc))
        print("Raw LLM output:", text)
        return fallback


def safe_jupyter_code_from_llm(
    system_prompt: str,
    user_content: str,
    fallback: str,
) -> str:
    """Ask the LLM for Jupyter-style code; return fallback if invalid."""
    llm = get_llm(temperature=0.1)
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt.strip()),
            HumanMessage(content=user_content),
        ]
    )
    text = response.content if isinstance(response.content, str) else str(response.content)
    text = strip_markdown_fence(text)

    if not text:
        print("LLM returned empty notebook code; using fallback.")
        return fallback

    if "# %%" not in text:
        print("LLM output does not look like Jupyter-style code; using fallback.")
        print("Raw LLM output:", text)
        return fallback

    return text


def business_analyst_node(state: dict[str, Any]) -> dict[str, Any]:
    user_query = state.get("user_query", "")
    clarification_history = state.get("clarification_history", [])

    llm_result = safe_json_from_llm(
        BA_PROMPT,
        json.dumps(
            {
                "user_query": user_query,
                "clarification_history": clarification_history,
            },
            ensure_ascii=False,
            indent=2,
        ),
        fallback={
            "scope_clear": False,
            "proposed_scope": {},
            "reason": "The scope is unclear.",
            "missing_information": ["strategy_type"],
            "next_question": "Do you want to test buy-and-hold/DCA, momentum timing, mean-reversion timing, or compare them?",
            "recommendation": "A practical default is to compare DCA, buy-and-hold, and a simple momentum timing rule.",
        },
    )

    scope_clear = bool(llm_result.get("scope_clear", False))
    next_question = llm_result.get("next_question")

    if not scope_clear and not next_question:
        raise ValueError("Invalid BA output: scope_clear is false, but next_question is missing.")

    return {
        **state,
        "scope": llm_result.get("proposed_scope", {}),
        "scope_clear": scope_clear,
        "ba_message": llm_result.get("reason", ""),
        "missing_information": llm_result.get("missing_information", []),
        "next_question": next_question,
        "recommendation": llm_result.get("recommendation", ""),
        "status": "scope_ready" if scope_clear else "need_user_scope_clarification",
    }


def filter_paper_node(state: dict[str, Any]) -> dict[str, Any]:
    scope = state.get("scope", {})
    scope_query = json.dumps(scope, ensure_ascii=False, default=str)

    research_keyword = safe_json_from_llm(
        ARXIV_QUERY_DECOMPOSER_PROMPT,
        f"Scope from user:\n{scope_query}",
        fallback={
            "queries": [
                "cat:q-fin.TR OR cat:q-fin.PM OR cat:q-fin.ST quantitative trading",
                "cat:q-fin.TR OR cat:q-fin.PM OR cat:q-fin.ST portfolio backtesting",
                "cat:q-fin.TR OR cat:q-fin.PM OR cat:q-fin.ST investment strategy",
            ]
        },
    )

    raw_candidates = search_papers(research_keyword)

    fallback_top = [
        {
            "paper_id": paper.get("paper_id", f"paper_{idx}"),
            "title": paper.get("title"),
            "arxiv_id": paper.get("arxiv_id", ""),
            "link": paper.get("link"),
            "authors": paper.get("authors", []),
            "published_date": paper.get("published_date", ""),
            "arxiv_categories": paper.get("arxiv_categories", []),
            "brief_summary": paper.get("brief_summary"),
            "scope_relevance_score": 50,
            "why_relevant_to_scope": "Fallback selection from retrieved candidates.",
            "possible_data_needed": "Historical price data, returns, and asset universe matching the paper as closely as possible.",
            "required_tools_or_methods": "Python, pandas, numpy, matplotlib, backtesting logic, statistical evaluation.",
            "rebuild_difficulty": "Medium",
            "rebuild_chance": "Medium",
            "reason_for_rebuild_chance": "Approximate reproduction may be possible, but exact replication depends on data availability.",
        }
        for idx, paper in enumerate(raw_candidates[:5], start=1)
    ]

    result = safe_json_from_llm(
        QR_PAPER_PROMPT,
        f"Scope:\n{scope_query}\n\nCandidate papers:\n{json.dumps(raw_candidates, ensure_ascii=False, default=str)}",
        fallback={
            "selected_papers": fallback_top,
            "paper_selection_message": "Please select one paper by paper_id.",
        },
    )

    top_papers = result.get("selected_papers") or result.get("top_papers") or fallback_top
    all_low = bool(top_papers) and all(
        str(paper.get("rebuild_chance") or paper.get("reproducibility_chance") or "")
        .lower()
        .strip()
        == "low"
        for paper in top_papers
    )

    return {
        "paper_candidates": raw_candidates,
        "top_papers": top_papers,
        "all_papers_low_chance": all_low,
        "paper_selection_message": result.get(
            "paper_selection_message", "Please select one paper by paper_id."
        ),
        "status": "papers_ranked",
    }


def read_paper_node(state: dict[str, Any]) -> dict[str, Any]:
    selected_id = state.get("selected_paper_id")
    top_papers = state.get("top_papers") or state.get("selected_papers") or []

    if not selected_id:
        return {
            "status": "awaiting_user_paper_selection",
            "paper_selection_message": "Please select one paper by paper_id.",
        }

    selected_paper = next((paper for paper in top_papers if paper.get("paper_id") == selected_id), None)

    if selected_paper is None:
        return {
            "selected_paper": None,
            "status": "invalid_paper_selection",
            "paper_selection_message": (
                f"Paper id '{selected_id}' was not found. Please choose one of the listed paper IDs."
            ),
        }

    link = selected_paper.get("link")
    pdf_url = selected_paper.get("pdf_url")

    if not link and not pdf_url:
        return {
            "selected_paper": selected_paper,
            "status": "paper_link_missing",
            "paper_selection_message": "Selected paper has no link or PDF URL, so PDF cannot be downloaded.",
        }

    try:
        pdf_url = pdf_url or get_arxiv_pdf_url(str(link))
        pdf_path = download_pdf_from_url(str(pdf_url))
        paper_text = extract_text_from_pdf(pdf_path)

        if not paper_text.strip():
            return {
                "selected_paper": selected_paper,
                "paper_pdf_url": str(pdf_url),
                "paper_pdf_path": str(pdf_path),
                "status": "paper_text_extraction_failed",
                "paper_selection_message": "PDF downloaded, but no text could be extracted.",
            }

        fallback_analysis = {
            "methodology": "",
            "main_results": "",
            "data_needed": "",
            "variables_or_features_needed": [],
            "models_or_methods": [],
            "backtest_or_experiment_design": "",
            "performance_metrics": [],
            "rebuild_steps": [],
            "rebuild_difficulty": "Medium",
            "rebuild_chance": "Medium",
            "limitations": "Fallback used because paper analysis failed.",
            "notebook_plan": [],
        }

        paper_analysis = safe_json_from_llm(
            PAPER_READING_PROMPT,
            (
                "Selected paper metadata:\n"
                f"{json.dumps(selected_paper, ensure_ascii=False, indent=2, default=str)}\n\n"
                "Extracted paper text:\n"
                f"{paper_text}"
            ),
            fallback=fallback_analysis,
        )

        output_data = {
            "selected_paper": selected_paper,
            "paper_pdf_url": str(pdf_url),
            "paper_pdf_path": str(pdf_path),
            "paper_text": paper_text,
            "paper_analysis": paper_analysis,
            "methodology": paper_analysis.get("methodology", ""),
            "main_results": paper_analysis.get("main_results", ""),
            "status": "paper_read",
        }

        output_dir = Path("outputs/paper_read")
        output_dir.mkdir(parents=True, exist_ok=True)
        paper_id = selected_paper.get("paper_id", "unknown_paper")
        json_path = output_dir / f"{paper_id}.json"
        json_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        output_data["paper_json_path"] = str(json_path)
        return output_data

    except Exception as exc:
        return {
            "selected_paper": selected_paper,
            "status": "paper_read_failed",
            "paper_selection_message": f"Failed to download or read selected paper: {exc}",
        }


def data_engineer_node(state: dict[str, Any]) -> dict[str, Any]:
    selected_paper = state.get("selected_paper")
    data_path = state.get("data_path")

    if not selected_paper:
        return {"data_ready": False, "data_issue": "No paper selected.", "status": "data_not_ready"}

    free_sources = find_free_data_sources(selected_paper)
    paid_sources = paid_data_recommendations(selected_paper)

    if data_path:
        return {
            "data_sources": free_sources,
            "paid_data_recommendations": [],
            "data_ready": True,
            "data_issue": None,
            "status": "data_ready",
        }

    downloadable = [source for source in free_sources if source.get("downloadable_by_agent")]
    if downloadable:
        return {
            "data_sources": free_sources,
            "paid_data_recommendations": [],
            "data_ready": False,
            "data_issue": (
                "Free downloadable data source exists, but this starter project does not automatically download it yet. "
                "Please add the connector or provide the downloaded file path with --data-path."
            ),
            "status": "need_user_data_help",
        }

    return {
        "data_sources": free_sources,
        "paid_data_recommendations": paid_sources,
        "data_ready": False,
        "data_issue": (
            "Suitable free data may require manual download, login, API key, or proxy data choice. "
            "Please provide a data file path or discuss a simpler data plan with the BA."
        ),
        "status": "data_not_ready",
    }


def quant_researcher_write_notebook_node(state: dict[str, Any]) -> dict[str, Any]:
    review = state.get("review")
    notebook_text = state.get("notebook_text")
    revision_count = int(state.get("revision_count", 0))
    paper_analysis = state.get("paper_analysis") or {}

    if not paper_analysis:
        raise ValueError("paper_analysis is missing. The paper must be read before writing the notebook.")

    paper_analysis_text = json.dumps(paper_analysis, indent=2, ensure_ascii=False, default=str)

    if not review:
        user_content = f"""
You are writing the initial notebook.

paper_analysis:
{paper_analysis_text}
"""
    else:
        review_text = json.dumps(
            {
                "review": review,
                "review_passed": state.get("review_passed", False),
                "review_comments": state.get("review_comments", ""),
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        )
        user_content = f"""
You are revising an existing Jupyter-style notebook based on reviewer feedback.

paper_analysis:
{paper_analysis_text}

previous_notebook_code:
{notebook_text}

review_feedback:
{review_text}

Revise the notebook directly. Keep the # %% and # %% [markdown] format.
Fix the concrete issues raised by the reviewer.
Return the full revised notebook code only.
"""

    text = safe_jupyter_code_from_llm(
        QUANT_RESEARCHER_WRITE_NOTEBOOK_PROMPT,
        user_content,
        fallback=notebook_text or "",
    )

    if not text or "# %%" not in text:
        raise ValueError("Notebook writer failed to produce valid Jupyter-style code.")

    notebook_path = jupyter_code_to_notebook(
        jupyter_code=text,
        output_path="notebooks/output/quant_research_notebook.ipynb",
    )

    return {
        "notebook_path": notebook_path,
        "notebook_summary": "Initial notebook drafted." if not review else "Notebook revised based on reviewer feedback.",
        "notebook_text": text,
        "revision_count": revision_count + 1 if review else revision_count,
        "status": "notebook_drafted",
    }


def reviewer_node(state: dict[str, Any]) -> dict[str, Any]:
    notebook_text = state.get("notebook_text")
    if not notebook_text:
        raise ValueError("notebook_text is missing. Cannot review notebook.")

    fallback = {
        "review": {
            "pros": [
                "The notebook has a readable structure for a GitHub research project.",
                "It includes objective, data, strategy, evaluation, limitations, and next-step sections.",
            ],
            "cons": [
                "The implementation may still need paper-specific formulas.",
                "Transaction costs, robustness tests, and statistical validation need to be verified manually.",
            ],
            "github_impressiveness": "Medium. The notebook is readable, but experienced reviewers will expect stronger empirical validation.",
            "research_gap_vs_original_paper": [
                "Exact original data may not be used.",
                "Backtest may not match the paper's methodology exactly.",
            ],
            "missing_robustness_tests": ["Subperiod and walk-forward tests should be added if absent."],
            "missing_transaction_costs": ["Transaction cost sensitivity should be added if absent."],
            "data_weakness": ["Proxy data assumptions should be disclosed."],
            "backtesting_weakness": ["Look-ahead bias and rebalancing assumptions should be checked."],
            "statistical_validation_weakness": ["Statistical significance tests should be added if absent."],
            "concrete_improvement_advice": [
                "Add transaction cost sensitivity.",
                "Add subperiod and walk-forward tests.",
                "Compare reproduced results with the paper's reported results.",
            ],
            "overall_score": 5,
        },
        "review_passed": False,
        "review_comments": "Fallback review used because model review failed. Manual review is recommended.",
    }

    result = safe_json_from_llm(REVIEWER_PROMPT, notebook_text, fallback=fallback)

    return {
        "review": result.get("review", {}),
        "review_passed": bool(result.get("review_passed", False)),
        "review_comments": result.get("review_comments", ""),
        "status": "review_passed" if result.get("review_passed", False) else "needs_revision",
    }
