from __future__ import annotations

from typing import Any, Literal, Optional
from typing_extensions import TypedDict, Annotated
import operator


class PaperDict(TypedDict, total=False):
    paper_id: str
    title: str
    link: str
    brief_summary: str
    required_data: str
    required_tools_or_methods: str
    difficulty: str
    reproducibility_chance: str
    reason_for_chance: str


class PaperAnalysisDict(TypedDict, total=False):
    methodology: str
    main_results: str
    data_needed: str
    variables_or_features_needed: list[str]
    models_or_methods: list[str]
    backtest_or_experiment_design: str
    performance_metrics: list[str]
    rebuild_steps: list[str]
    rebuild_difficulty: str
    rebuild_chance: str
    limitations: str
    notebook_plan: list[str]


class ReviewDict(TypedDict, total=False):
    pros: list[str]
    cons: list[str]
    github_impressiveness: str
    research_gap_vs_original_paper: list[str]
    missing_robustness_tests: list[str]
    missing_transaction_costs: list[str]
    data_weakness: list[str]
    backtesting_weakness: list[str]
    statistical_validation_weakness: list[str]
    concrete_improvement_advice: list[str]
    overall_score: int


class QuantWorkflowState(TypedDict, total=False):
    # --------------------------------------------------
    # Input from previous manual steps
    # --------------------------------------------------
    selected_paper_id: str
    top_papers: list[PaperDict]
    selected_papers: list[PaperDict]



    # --------------------------------------------------
    # read_paper_node output
    # --------------------------------------------------
    selected_paper: Optional[PaperDict]
    paper_pdf_url: str
    paper_pdf_path: str
    paper_text: str
    paper_analysis: PaperAnalysisDict
    methodology: str
    main_results: str


    paper_selection_message: str

    # --------------------------------------------------
    # quant_researcher_write_notebook_node output
    # --------------------------------------------------
    notebook_path: str
    notebook_summary: str
    notebook_text: str

    # --------------------------------------------------
    # reviewer_node output
    # --------------------------------------------------
    review: ReviewDict
    review_passed: bool
    review_comments: str

    # for revision loop
    revision_count: int

    # --------------------------------------------------
    # General status
    # --------------------------------------------------
    status: Literal[
        "awaiting_user_paper_selection",
        "invalid_paper_selection",
        "paper_link_missing",
        "paper_text_extraction_failed",
        "paper_read",
        "paper_read_failed",
        "notebook_drafted",
        "notebook_reviewed",
        "review_passed",
        "needs_revision",
    ]

    # Important: this allows each node to append logs
    logs: Annotated[list[dict[str, Any]], operator.add]
