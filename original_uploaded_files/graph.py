from __future__ import annotations

from typing import Literal

from langgraph.graph import StateGraph, START, END
from .monitor import monitor_node
from .state import QuantWorkflowState
from .agents import (

    quant_researcher_write_notebook_node,
    reviewer_node,
    read_paper_node

)

MAX_REVISIONS = 3

def route_after_reviewer(
    state: QuantWorkflowState,
) -> Literal["revise", "end"]:
    review_passed = state.get("review_passed", False)
    revision_count = state.get("revision_count", 0)

    if review_passed:
        return "end"

    if revision_count >= MAX_REVISIONS:
        return "end"

    return "revise"




def build_graph():
    graph = StateGraph(QuantWorkflowState)

    graph.add_node(
        "read_paper_node",
        monitor_node("read_paper_node", read_paper_node)
    )

    graph.add_node(
        "quant_researcher_write_notebook",
        monitor_node(
            "quant_researcher_write_notebook",
            quant_researcher_write_notebook_node
        )
    )

    graph.add_node(
        "reviewer",
        monitor_node("reviewer", reviewer_node)
    )

    graph.add_edge(START, "read_paper_node")
    graph.add_edge("read_paper_node", "quant_researcher_write_notebook")
    graph.add_edge("quant_researcher_write_notebook", "reviewer")

    graph.add_conditional_edges(
        "reviewer",
        route_after_reviewer,
        {
            "end": END,
            "revise": "quant_researcher_write_notebook",
        }
    )

    return graph.compile()


