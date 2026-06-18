from __future__ import annotations

from pathlib import Path
from typing import Any

import nbformat as nbf


def jupyter_code_to_notebook(
    jupyter_code: str,
    output_path: str = "notebooks/output/quant_research_notebook.ipynb",
) -> str:
    """Convert Jupyter-style Python code with # %% markers into an ipynb file."""
    nb = nbf.v4.new_notebook()
    cells = []

    current_cell_type = "code"
    current_lines: list[str] = []

    def flush_cell() -> None:
        nonlocal current_lines, current_cell_type, cells
        if not current_lines:
            return

        source = "\n".join(current_lines).strip()
        current_lines = []
        if not source:
            return

        if current_cell_type == "markdown":
            cells.append(nbf.v4.new_markdown_cell(source))
        else:
            cells.append(nbf.v4.new_code_cell(source))

    for line in jupyter_code.splitlines():
        stripped = line.strip()

        if stripped.startswith("# %%"):
            flush_cell()
            current_cell_type = "markdown" if "[markdown]" in stripped.lower() else "code"
            continue

        if current_cell_type == "markdown":
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


def write_initial_notebook(
    selected_paper: dict[str, Any],
    cleaned_data_path: str | None,
    output_path: str = "notebooks/output/quant_research_notebook.ipynb",
) -> str:
    """Write a simple fallback notebook when LLM notebook generation is unavailable."""
    paper_title = selected_paper.get("title", "Selected Quant Research Paper")
    paper_link = selected_paper.get("link", "")
    summary = selected_paper.get("brief_summary", "")

    nb = nbf.v4.new_notebook()
    nb["cells"] = [
        nbf.v4.new_markdown_cell(
            f"""# Rebuilding a Quantitative Research Paper

## Selected paper

**Title:** {paper_title}

**Link:** {paper_link}

## Research objective

This notebook rebuilds the core idea of the selected paper in a practical, transparent way.  
The goal is not to perfectly replicate every institutional detail, but to create a readable and testable quantitative research prototype.

## Paper summary

{summary}
"""
        ),
        nbf.v4.new_markdown_cell(
            """## Reproduction plan

1. Load and inspect the dataset.
2. Clean timestamps, prices, and missing values.
3. Construct returns and research features.
4. Implement the paper's core signal or model.
5. Build a transparent backtest or evaluation framework.
6. Evaluate performance with charts and tables.
7. Discuss limitations and research gaps.
"""
        ),
        nbf.v4.new_code_cell(
            """import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

pd.set_option("display.max_columns", 100)
"""
        ),
        nbf.v4.new_markdown_cell("## 1. Load data"),
        nbf.v4.new_code_cell(
            f"""DATA_PATH = r"{cleaned_data_path or 'PUT_YOUR_DATA_PATH_HERE.csv'}"

try:
    df = pd.read_csv(DATA_PATH)
    display(df.head())
    print(df.shape)
except FileNotFoundError:
    print("Data file not found. Please update DATA_PATH.")
"""
        ),
    ]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, path)
    return str(path)


def format_list(items: Any) -> str:
    if isinstance(items, str):
        return items
    if not items:
        return "- Not provided."
    return "\n".join(f"- {item}" for item in items)


def write_revised_notebook(
    initial_path: str,
    review: dict[str, Any],
    output_path: str = "notebooks/output/final_quant_research_notebook.ipynb",
) -> str:
    """Append reviewer comments and revision notes to an existing notebook."""
    nb = nbf.read(initial_path, as_version=4)

    review_md = f"""# Reviewer feedback and revision notes

## Pros
{format_list(review.get("pros", []))}

## Cons
{format_list(review.get("cons", []))}

## GitHub impressiveness
{review.get("github_impressiveness", "Not provided.")}

## Research gap vs original paper
{format_list(review.get("research_gap_vs_original_paper", []))}

## Concrete improvement advice
{format_list(review.get("concrete_improvement_advice", []))}
"""

    nb["cells"].append(nbf.v4.new_markdown_cell(review_md))
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, path)
    return str(path)
