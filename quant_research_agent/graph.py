from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from .agents import (
    build_paper_graph_node,
    paper_analysis_from_graph_node,
    quant_researcher_write_notebook_node,
    read_paper_node,
    reviewer_node,
)
from .monitor import monitor_node
from .state import QuantWorkflowState

MAX_REVISIONS = 3


def route_after_read_paper(state: QuantWorkflowState) -> Literal["build_graph", "end"]:
    return "build_graph" if state.get("status") == "paper_extracted" else "end"


def route_after_paper_graph(state: QuantWorkflowState) -> Literal["analyze", "end"]:
    return "analyze" if state.get("status") == "paper_graph_built" else "end"


def route_after_paper_analysis(state: QuantWorkflowState) -> Literal["write", "end"]:
    return "write" if state.get("status") == "paper_read" else "end"


def route_after_writer(state: QuantWorkflowState) -> Literal["review", "end"]:
    return "review" if state.get("status") == "notebook_drafted" else "end"


def route_after_reviewer(state: QuantWorkflowState) -> Literal["revise", "end"]:
    review_passed = state.get("review_passed", False)
    revision_count = state.get("revision_count", 0)

    if review_passed:
        return "end"
    if revision_count >= MAX_REVISIONS:
        return "end"
    return "revise"


def build_graph():
    """Build the notebook generation graph.

    Flow:
    read paper -> build paper KG -> graph-based analysis -> write notebook -> review/revise
    """
    graph = StateGraph(QuantWorkflowState)

    graph.add_node("read_paper_node", monitor_node("read_paper_node", read_paper_node))
    graph.add_node("build_paper_graph", monitor_node("build_paper_graph", build_paper_graph_node))
    graph.add_node(
        "paper_analysis_from_graph",
        monitor_node("paper_analysis_from_graph", paper_analysis_from_graph_node),
    )
    graph.add_node(
        "quant_researcher_write_notebook",
        monitor_node("quant_researcher_write_notebook", quant_researcher_write_notebook_node),
    )
    graph.add_node("reviewer", monitor_node("reviewer", reviewer_node))

    graph.add_edge(START, "read_paper_node")

    graph.add_conditional_edges(
        "read_paper_node",
        route_after_read_paper,
        {"build_graph": "build_paper_graph", "end": END},
    )

    graph.add_conditional_edges(
        "build_paper_graph",
        route_after_paper_graph,
        {"analyze": "paper_analysis_from_graph", "end": END},
    )

    graph.add_conditional_edges(
        "paper_analysis_from_graph",
        route_after_paper_analysis,
        {"write": "quant_researcher_write_notebook", "end": END},
    )

    graph.add_conditional_edges(
        "quant_researcher_write_notebook",
        route_after_writer,
        {"review": "reviewer", "end": END},
    )

    graph.add_conditional_edges(
        "reviewer",
        route_after_reviewer,
        {"end": END, "revise": "quant_researcher_write_notebook"},
    )

    return graph.compile()