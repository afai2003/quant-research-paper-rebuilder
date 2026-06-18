from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from .llm import get_llm
from .prompts import BA_PROMPT, QR_PAPER_PROMPT, QUANT_RESEARCHER_WRITE_NOTEBOOK_PROMPT, REVIEWER_PROMPT, ARXIV_QUERY_DECOMPOSER_PROMPT,PAPER_READING_PROMPT
from .tools import search_papers, find_free_data_sources, paid_data_recommendations,get_arxiv_pdf_url,download_pdf_from_url,extract_text_from_pdf
from .notebook_writer import  write_revised_notebook
from pathlib import Path

def safe_jupyter_code_from_llm(
    system_prompt: str,
    user_content: str,
    fallback: str,
) -> str:


    llm = get_llm(temperature=0.1)



    response = llm.invoke(
        [
            SystemMessage(
                content=system_prompt.strip()
            ),
            HumanMessage(content=user_content),
        ]
    )

    text = response.content if isinstance(response.content, str) else str(response.content)

    text = text.strip()

    # Remove markdown fence if LLM accidentally returns it
    if text.startswith("```python"):
        text = text.removeprefix("```python").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").strip()

    if text.endswith("```"):
        text = text.removesuffix("```").strip()

    if not text:
        print("LLM returned empty notebook code.")
        return fallback

    if "# %%" not in text:
        print("LLM output does not look like Jupyter-style code.")
        print("Raw LLM output:")
        print(text)
        return fallback

    return text


def safe_json_from_llm(system_prompt: str, user_content: str, fallback: dict[str, Any]) -> dict[str, Any]:
    """Ask LLM for JSON. If parsing fails, return fallback."""
    llm = get_llm(temperature=0.1)
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt + "\nReturn valid JSON only. No markdown."),
            HumanMessage(content=user_content),
        ]
    )
    text = response.content if isinstance(response.content, str) else str(response.content)

    try:
        
        return json.loads(text)
    except Exception as e:
        print("JSON parsing failed.")
        print("Error type:", type(e).__name__)
        print("Error message:", str(e))
        print("Raw LLM output:")
        print(text)

        return fallback


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
            "recommendation": "For monthly US index ETF investing, a good default is to compare DCA, buy-and-hold, and simple momentum timing.",
        },
    )
    print("rrrrrrrrrrrrrrrrrrrrrrrrrrrr")
    print(llm_result )
    print("rrrrrrrrrrrrrrrrrrrrrrrrrrrr")

    scope_clear = llm_result.get("scope_clear", False)
    next_question = llm_result.get("next_question")

    if not scope_clear and not next_question:
        raise ValueError(
            "Invalid BA output: scope_clear is false, but next_question is missing."
        )

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
    scope_query = json.dumps(scope, ensure_ascii=False)
    fallback = {}
    research_keyword = safe_json_from_llm(
        ARXIV_QUERY_DECOMPOSER_PROMPT,
        f"Scope from user: {scope_query}",
        fallback=fallback,
    )


    raw_candidates = search_papers(research_keyword)

    fallback_top = []
    for i, p in enumerate(raw_candidates[:5], start=1):
        fallback_top.append(
            {
                "paper_id": p.get("paper_id", f"paper_{i}"),
                "title": p.get("title"),
                "link": p.get("link"),
                "brief_summary": p.get("brief_summary"),
                "required_data": "Historical price data, returns, and asset universe matching the paper as closely as possible.",
                "required_tools_or_methods": "Python, pandas, numpy, matplotlib, backtesting logic, statistical evaluation.",
                "difficulty": "Medium",
                "reproducibility_chance": "Medium",
                "reason_for_chance": "Approximate reproduction may be possible, but exact replication depends on data availability.",
            }
        )

    fallback = {
        "top_papers": fallback_top,
        "paper_selection_message": "Please select one paper by paper_id.",
    }

    result = safe_json_from_llm(
        QR_PAPER_PROMPT,
        f"Scope:\n{scope_query}\n\nCandidate papers:\n{json.dumps(raw_candidates, ensure_ascii=False)}",
        fallback=fallback,
    )


    #top_papers = result.get("top_papers", fallback_top)
    top_papers = result.get("selected_papers")
    all_low = all(str(p.get("reproducibility_chance", "")).lower() == "low" for p in top_papers)

    return {
        "paper_candidates": raw_candidates,
        "top_papers": top_papers,
        "all_papers_low_chance": all_low,
        "paper_selection_message": result.get("paper_selection_message", "Please select one paper by paper_id."),
        "status": "papers_ranked",
    }


def read_paper_node(state: dict[str, Any]) -> dict[str, Any]:
    selected_id = state.get("selected_paper_id")

    top_papers = (
        state.get("top_papers")
        or state.get("selected_papers")
        or []
    )


    if not selected_id:
        return {
            "status": "awaiting_user_paper_selection",
            "paper_selection_message": "Please select one paper by paper_id.",
        }

    selected_paper = None

    for p in top_papers:
        if p.get("paper_id") == selected_id:
            selected_paper = p
            break

    if selected_paper is None:
        return {
            "selected_paper": None,
            "status": "invalid_paper_selection",
            "paper_selection_message": (
                f"Paper id '{selected_id}' was not found. "
                "Please choose one of the top paper IDs."
            ),
        }

    link = selected_paper.get("link")


    if not link:
        return {
            "selected_paper": selected_paper,
            "status": "paper_link_missing",
            "paper_selection_message": "Selected paper has no link, so PDF cannot be downloaded.",
        }

    try:
        pdf_url = get_arxiv_pdf_url(link)
        pdf_path = download_pdf_from_url(pdf_url)
        paper_text = extract_text_from_pdf(pdf_path)

        if not paper_text.strip():
            return {
                "selected_paper": selected_paper,
                "paper_pdf_url": pdf_url,
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
                f"{json.dumps(selected_paper, ensure_ascii=False, indent=2)}\n\n"
                "Extracted paper text:\n"
                f"{paper_text}"
            ),
            fallback=fallback_analysis,
        )

        output_data = {
            "selected_paper": selected_paper,
            "paper_pdf_url": pdf_url,
            "paper_pdf_path": str(pdf_path),
            "paper_text": paper_text,
            "paper_analysis": paper_analysis,
            "methodology": paper_analysis.get("methodology", ""),
            "main_results": paper_analysis.get("main_results", ""),
            "status": "paper_read",
        }

        # --------------------------------------------------
        # Save paper reading result as JSON
        # --------------------------------------------------

        output_dir = Path("outputs/paper_read")
        output_dir.mkdir(parents=True, exist_ok=True)

        paper_id = selected_paper.get("paper_id", "unknown_paper")


        json_path = output_dir / f"{paper_id}.json"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                output_data,
                f,
                ensure_ascii=False,
                indent=2,
                default=str,   # handles datetime / non-json objects
            )

        output_data["paper_json_path"] = str(json_path)

        return output_data



    except Exception as e:
        print(e)
        return {
            "selected_paper": selected_paper,
            "status": "paper_read_failed",
            "paper_selection_message": f"Failed to download or read selected paper: {e}",
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

    downloadable = [s for s in free_sources if s.get("downloadable_by_agent")]
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

from pathlib import Path
from typing import Any
import nbformat as nbf


def jupyter_code_to_notebook(
    jupyter_code: str,
    output_path: str = "notebooks/output/quant_research_notebook.ipynb",
) -> str:
    """Convert Jupyter-style Python code with # %% markers into .ipynb."""

    nb = nbf.v4.new_notebook()
    cells = []

    current_cell_type = "code"
    current_lines = []

    def flush_cell():
        nonlocal current_lines, current_cell_type, cells

        if not current_lines:
            return

        source = "\n".join(current_lines).strip()

        if not source:
            current_lines = []
            return

        if current_cell_type == "markdown":
            cells.append(nbf.v4.new_markdown_cell(source))
        else:
            cells.append(nbf.v4.new_code_cell(source))

        current_lines = []

    for line in jupyter_code.splitlines():
        stripped = line.strip()

        if stripped.startswith("# %%"):
            flush_cell()

            if "[markdown]" in stripped.lower():
                current_cell_type = "markdown"
            else:
                current_cell_type = "code"

            continue

        if current_cell_type == "markdown":
            # Convert commented markdown into normal markdown
            if line.startswith("# "):
                current_lines.append(line[2:])
            elif line.startswith("#"):
                current_lines.append(line[1:])
            else:
                current_lines.append(line)
        else:
            current_lines.append(line)

    flush_cell()

    nb["cells"] = cells

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    nbf.write(nb, path)

    return str(path)



def quant_researcher_write_notebook_node(state: dict[str, Any]) -> dict[str, Any]:
    review = state.get("review")
    notebook_text = state.get("notebook_text")
    revision_count = state.get("revision_count", 0)

    paper_analysis = state.get("paper_analysis") or {}
    paper_analysis_text = json.dumps(
        paper_analysis,
        indent=2,
        ensure_ascii=False,
        default=str,
    )

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
        "notebook_summary": (
            "Initial notebook drafted."
            if not review
            else "Notebook revised based on reviewer feedback."
        ),
        "notebook_text": text,
        "revision_count": revision_count + 1 if review else revision_count,
        "status": "notebook_drafted",
    }


def reviewer_node(state: dict[str, Any]) -> dict[str, Any]:
    notebook_text = state.get("notebook_text")


    fallback = {
        "pros": [
            "Clear structure for a GitHub research notebook.",
            "Paper link, objective, data section, strategy section, evaluation, limitations, and next steps are included.",
        ],
        "cons": [
            "The strategy logic is still a template and must be customized to the selected paper.",
            "No transaction cost model has been implemented yet.",
            "No robustness tests or statistical significance tests have been added yet.",
        ],
        "impressiveness": "Medium. The notebook is readable and professional, but it needs paper-specific implementation and stronger empirical validation to impress an experienced quant researcher.",
        "research_gap": [
            "Exact original data may not be used.",
            "Portfolio construction may be simplified.",
            "Backtest may not match the paper's methodology.",
            "Statistical validation is incomplete.",
        ],
        "improvement_advice": [
            "Add transaction cost sensitivity.",
            "Add subperiod and walk-forward tests.",
            "Compare reproduced results with the paper's reported results.",
            "Add a section explaining assumptions and deviations from the original paper.",
        ],
    }

    result = safe_json_from_llm(
        REVIEWER_PROMPT,
        notebook_text,
        fallback=fallback,
    )


    return {
    "review": result.get("review", {}),
    "review_passed": result.get("review_passed", False),
    "review_comments": result.get("review_comments", ""),
    "status": "review_passed" if result.get("review_passed", False) else "needs_revision",
}


