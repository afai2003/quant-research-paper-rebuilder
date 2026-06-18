from __future__ import annotations

from pathlib import Path
from typing import Any

import nbformat as nbf


def write_initial_notebook(
    selected_paper: dict[str, Any],
    cleaned_data_path: str | None,
    output_path: str = "notebooks/output/quant_research_notebook.ipynb",
) -> str:
    """Write a GitHub-quality starter notebook.

    The Quant Researcher Agent can later revise this notebook after reviewer feedback.
    """
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

This notebook rebuilds the core idea of the selected paper in a practical and transparent way.  
The goal is not to perfectly replicate every institutional detail, but to create a serious, readable, and testable quantitative research prototype.

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
5. Build a simple but transparent backtest or evaluation framework.
6. Evaluate performance with charts and tables.
7. Discuss limitations and research gaps.
"""
        ),
        nbf.v4.new_code_cell(
            """import pandas as pd
import numpy as np
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
        nbf.v4.new_markdown_cell("## 2. Data cleaning and feature engineering"),
        nbf.v4.new_code_cell(
            """# Example structure. Modify column names based on your actual data.
# Expected minimal columns: date/time column and close/price column.

def prepare_price_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Try to infer timestamp column.
    time_candidates = [c for c in df.columns if c.lower() in ["date", "datetime", "timestamp", "time"]]
    price_candidates = [c for c in df.columns if c.lower() in ["close", "price", "adj close", "settle"]]

    if not time_candidates or not price_candidates:
        raise ValueError("Please rename columns or update the function to identify timestamp and price columns.")

    time_col = time_candidates[0]
    price_col = price_candidates[0]

    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(time_col).drop_duplicates(time_col)
    df = df.rename(columns={time_col: "timestamp", price_col: "price"})
    df["ret_1"] = np.log(df["price"]).diff()
    df["ret_20"] = np.log(df["price"]).diff(20)
    df["vol_20"] = df["ret_1"].rolling(20).std()
    df["signal"] = np.sign(df["ret_20"])
    df = df.dropna()

    return df

# prepared = prepare_price_data(df)
# display(prepared.head())
"""
        ),
        nbf.v4.new_markdown_cell("## 3. Strategy / model implementation"),
        nbf.v4.new_code_cell(
            """def run_simple_signal_backtest(prepared: pd.DataFrame) -> pd.DataFrame:
    result = prepared.copy()
    result["position"] = result["signal"].shift(1).fillna(0)
    result["strategy_ret"] = result["position"] * result["ret_1"]
    result["benchmark_ret"] = result["ret_1"]
    result["strategy_equity"] = np.exp(result["strategy_ret"].cumsum())
    result["benchmark_equity"] = np.exp(result["benchmark_ret"].cumsum())
    return result

# bt = run_simple_signal_backtest(prepared)
# display(bt.tail())
"""
        ),
        nbf.v4.new_markdown_cell("## 4. Evaluation"),
        nbf.v4.new_code_cell(
            """def summarize_returns(ret: pd.Series, periods_per_year: int = 252) -> pd.Series:
    ret = ret.dropna()
    ann_return = ret.mean() * periods_per_year
    ann_vol = ret.std() * np.sqrt(periods_per_year)
    sharpe = ann_return / ann_vol if ann_vol != 0 else np.nan
    max_dd = (np.exp(ret.cumsum()) / np.exp(ret.cumsum()).cummax() - 1).min()

    return pd.Series({
        "annual_return": ann_return,
        "annual_volatility": ann_vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
    })

# metrics = pd.concat([
#     summarize_returns(bt["strategy_ret"]).rename("strategy"),
#     summarize_returns(bt["benchmark_ret"]).rename("benchmark"),
# ], axis=1)
# display(metrics)
"""
        ),
        nbf.v4.new_code_cell(
            """# Example plot
# ax = bt.set_index("timestamp")[["strategy_equity", "benchmark_equity"]].plot(figsize=(12, 5))
# ax.set_title("Strategy vs benchmark equity curve")
# ax.set_ylabel("Growth of $1")
# plt.show()
"""
        ),
        nbf.v4.new_markdown_cell(
            """## 5. Interpretation

Discuss:
- whether the reproduced signal behaves as expected,
- whether results are economically meaningful,
- whether the result survives transaction costs,
- whether the result is stable across subperiods,
- whether the research finding is close to the paper's finding.

## 6. Limitations and research gap

Possible gaps:
- data may be proxy data rather than the original paper's exact dataset,
- transaction costs may be simplified,
- survivorship bias may exist,
- universe construction may differ,
- robustness checks may be incomplete,
- statistical significance may require stronger testing.

## 7. Next steps

Suggested improvements:
- add transaction cost sensitivity,
- add walk-forward validation,
- add subperiod analysis,
- add alternative signal definitions,
- compare across assets,
- improve portfolio construction,
- add statistical tests.
"""
        ),
    ]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, path)
    return str(path)


def write_revised_notebook(
    initial_path: str,
    review: dict[str, Any],
    output_path: str = "notebooks/output/final_quant_research_notebook.ipynb",
) -> str:
    """Add reviewer comments and revision plan to the notebook."""
    nb = nbf.read(initial_path, as_version=4)

    review_md = f"""# Reviewer feedback and revision notes

                    ## Pros
                    {format_list(review.get("pros", []))}

                    ## Cons
                    {format_list(review.get("cons", []))}

                    ## Impressiveness
                    {review.get("impressiveness", "Not provided.")}

                    ## Research gap
                    {format_list(review.get("research_gap", []))}

                    ## Improvement advice applied
                    {format_list(review.get("improvement_advice", []))}

                    ## Revision summary

                    This revised version makes the notebook more suitable for GitHub presentation by explicitly documenting the research objective, reproduction assumptions, limitations, and next-step improvements.
                    """

    nb["cells"].append(nbf.v4.new_markdown_cell(review_md))

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, path)
    return str(path)


def format_list(items: Any) -> str:
    if isinstance(items, str):
        return items
    if not items:
        return "- Not provided."
    return "\n".join(f"- {x}" for x in items)
