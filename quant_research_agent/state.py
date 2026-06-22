from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, Optional
from typing_extensions import TypedDict


class PaperDict(TypedDict, total=False):
    paper_id: str
    title: str
    arxiv_id: str
    link: str
    pdf_url: str
    brief_summary: str
    authors: list[str]
    published_date: str
    arxiv_categories: list[str]
    required_data: str
    required_tools_or_methods: str
    rebuild_difficulty: str
    rebuild_chance: str
    reason_for_rebuild_chance: str


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
    notebook_plan: list[dict[str, str]]


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
    # User / BA stage
    user_query: str
    clarification_history: list[dict[str, str]]
    scope: dict[str, Any] | str
    scope_clear: bool
    ba_message: str
    missing_information: list[str]
    next_question: Optional[str]
    recommendation: str

    # Paper filtering and selection
    selected_paper_id: str
    paper_candidates: list[PaperDict]
    top_papers: list[PaperDict]
    selected_papers: list[PaperDict]
    all_papers_low_chance: bool
    paper_selection_message: str

    # Paper reading
    selected_paper: Optional[PaperDict]
    paper_pdf_url: str
    paper_pdf_path: str
    paper_json_path: str
    paper_text: str
    paper_analysis: PaperAnalysisDict
    methodology: str
    main_results: str

    # Notebook writing
    notebook_path: str
    notebook_summary: str
    notebook_text: str

    # Review loop
    review: ReviewDict
    review_passed: bool
    review_comments: str
    revision_count: int

    # General
    status: Literal[
        "scope_ready",
        "need_user_scope_clarification",
        "papers_ranked",
        "awaiting_user_paper_selection",
        "invalid_paper_selection",
        "paper_link_missing",
        "paper_text_extraction_failed",
        "paper_read",
        "paper_read_failed",
        "notebook_drafted",
        "review_passed",
        "needs_revision",
        "error",
        "paper_extracted",
        "paper_graph_built",
        "paper_graph_failed",
    ]
    error_message: str
    logs: Annotated[list[dict[str, Any]], operator.add]

    paper_chunks: list[PaperChunkDict]
    paper_graph: PaperGraphDict
    paper_graph_path: str
    paper_graph_context: str


class PaperChunkDict(TypedDict, total=False):
    chunk_id: str
    page: int
    text: str


class PaperGraphNodeDict(TypedDict, total=False):
    node_id: str
    type: str
    label: str
    description: str
    evidence: list[dict[str, Any]]


class PaperGraphEdgeDict(TypedDict, total=False):
    source: str
    target: str
    relation: str
    evidence: list[dict[str, Any]]


class PaperGraphDict(TypedDict, total=False):
    nodes: list[PaperGraphNodeDict]
    edges: list[PaperGraphEdgeDict]
    implementation_steps: list[dict[str, Any]]
    missing_or_unclear: list[str]