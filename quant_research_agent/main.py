from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_research_agent.agents import business_analyst_node, filter_paper_node
from quant_research_agent.graph import build_graph


def ask_yes_no(prompt: str) -> bool:
    while True:
        answer = input(f"{prompt} [y/n]: ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please enter y or n.")


def ask_text(prompt: str) -> str:
    return input(f"{prompt}: ").strip()


def print_scope(result: dict[str, Any]) -> None:
    print("\n=== PROPOSED RESEARCH SCOPE ===")
    print(json.dumps(result.get("scope", {}), indent=2, ensure_ascii=False, default=str))

    if result.get("ba_message"):
        print("\nBA Message:")
        print(result["ba_message"])

    if result.get("recommendation"):
        print("\nRecommendation:")
        print(result["recommendation"])


def print_top_papers(result: dict[str, Any]) -> None:
    print("\n=== SELECTED PAPERS ===")
    selected_papers = result.get("top_papers", [])

    if not selected_papers:
        print("No selected papers found.")
        return

    for paper in selected_papers:
        print("\n" + "-" * 80)
        print(f"Paper ID: {paper.get('paper_id')}")
        print(f"Title: {paper.get('title')}")
        print(f"arXiv ID: {paper.get('arxiv_id')}")
        print(f"Link: {paper.get('link')}")

        authors = paper.get("authors", [])
        if isinstance(authors, list):
            authors = ", ".join(authors)
        print(f"Authors: {authors}")

        categories = paper.get("arxiv_categories", [])
        if isinstance(categories, list):
            categories = ", ".join(categories)

        print(f"Published Date: {paper.get('published_date')}")
        print(f"arXiv Categories: {categories}")
        print(f"Brief Summary: {paper.get('brief_summary')}")
        print(f"Scope Relevance Score: {paper.get('scope_relevance_score')}")
        print(f"Why Relevant to Scope: {paper.get('why_relevant_to_scope')}")
        print(f"Evidence from Brief Summary: {paper.get('evidence_from_brief_summary')}")
        print(f"Possible Data Needed: {paper.get('possible_data_needed')}")
        print(f"Required Tools or Methods: {paper.get('required_tools_or_methods')}")
        print(f"Rebuild Difficulty: {paper.get('rebuild_difficulty')}")
        print(f"Rebuild Chance: {paper.get('rebuild_chance')}")
        print(f"Reason for Rebuild Chance: {paper.get('reason_for_rebuild_chance')}")


def save_state(result: dict[str, Any], save_path: str) -> None:
    path = Path(save_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nState saved to: {path}")


def run_notebook_graph(
    top_papers: list[dict[str, Any]],
    selected_paper_id: str,
) -> dict[str, Any]:
    notebook_app = build_graph()
    graph_state = {
        "selected_paper_id": selected_paper_id,
        "top_papers": top_papers,
        "revision_count": 0,
        "logs": [],
    }

    final_state: dict[str, Any] = {}

    for mode, chunk in notebook_app.stream(
        graph_state,
        {"recursion_limit": 20},
        stream_mode=["custom", "updates", "values"],
    ):
        if mode == "custom":
            print(
                f"[{chunk.get('time')}] "
                f"{chunk.get('node')} | "
                f"{chunk.get('event')} | "
                f"{chunk.get('message')}"
            )
        elif mode == "updates":
            for node_name, update in chunk.items():
                print(f"\n--- Node finished: {node_name} ---")
                print("Updated keys:", list(update.keys()))
        elif mode == "values":
            final_state = chunk

    return final_state


def run_paper_filter(scope: Any) -> dict[str, Any]:
    result = filter_paper_node({"scope": scope})
    print_top_papers(result)
    return result


def run_interactive(args: argparse.Namespace) -> None:
    query = args.query
    selected_paper_id = args.selected_paper_id
    clarification_history: list[dict[str, str]] = []
    ba_state: dict[str, Any] = {"user_query": query, "clarification_history": clarification_history}

    while True:
        result = business_analyst_node(ba_state)
        print_scope(result)

        if result.get("scope_clear", False):
            approved = ask_yes_no("\nDo you approve this scope?")
            if approved:
                print("\nScope approved. Proceeding to paper filtering...")
                break

            user_feedback = ask_text("\nWhat would you like to change in the scope")
            clarification_history.append(
                {
                    "question": "User rejected the proposed scope. What changes should be made?",
                    "answer": user_feedback,
                }
            )
            ba_state = {
                "user_query": (
                    f"Original user query:\n{args.query}\n\n"
                    f"Previously proposed scope:\n{json.dumps(result.get('scope', {}), ensure_ascii=False, indent=2)}\n\n"
                    f"User feedback:\n{user_feedback}"
                ),
                "clarification_history": clarification_history,
            }
            continue

        next_question = result.get("next_question")
        if not next_question:
            print("\nBA says scope is unclear, but no next question was returned.")
            save_state(result, args.save_state)
            return

        print("\nBA needs clarification:")
        print(next_question)
        user_answer = ask_text("\nYour answer")
        clarification_history.append({"question": next_question, "answer": user_answer})
        ba_state = {
            "user_query": f"Original user query:\n{args.query}",
            "clarification_history": clarification_history,
        }

    paper_result = run_paper_filter(result.get("scope", {}))

    if paper_result.get("all_papers_low_chance"):
        print("\nAll selected papers have low rebuild chance. Consider refining the scope.")
        save_state({**result, **paper_result}, args.save_state)
        return

    if not selected_paper_id:
        selected_paper_id = ask_text("\nPlease choose a paper_id to rebuild, e.g. arxiv_1")

    notebook_result = run_notebook_graph(paper_result.get("top_papers", []), selected_paper_id)
    final_result = {**result, **paper_result, **notebook_result}

    print("\nNotebook workflow completed.")
    print(f"Status: {final_result.get('status')}")
    print(f"Notebook path: {final_result.get('notebook_path')}")
    save_state(final_result, args.save_state)


def run_once(args: argparse.Namespace) -> None:
    ba_result = business_analyst_node(
        {
            "user_query": args.query,
            "clarification_history": [],
        }
    )
    print_scope(ba_result)

    if not ba_result.get("scope_clear", False):
        print("\nScope is not clear enough yet. Run with --interactive or answer this question:")
        print(ba_result.get("next_question"))
        save_state(ba_result, args.save_state)
        return

    paper_result = run_paper_filter(ba_result.get("scope", {}))

    if paper_result.get("all_papers_low_chance"):
        print("\nAll selected papers have low rebuild chance. Consider refining the scope.")
        save_state({**ba_result, **paper_result}, args.save_state)
        return

    if not args.selected_paper_id:
        print("\nPaper filtering completed. Re-run with --selected-paper-id to build a notebook.")
        save_state({**ba_result, **paper_result}, args.save_state)
        return

    notebook_result = run_notebook_graph(paper_result.get("top_papers", []), args.selected_paper_id)
    final_result = {**ba_result, **paper_result, **notebook_result}

    print("\nNotebook workflow completed.")
    print(f"Status: {final_result.get('status')}")
    print(f"Notebook path: {final_result.get('notebook_path')}")
    save_state(final_result, args.save_state)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Quant Research Paper Rebuilding Agent workflow.")
    parser.add_argument("--query", required=True, help="User's quantitative research idea.")
    parser.add_argument("--selected-paper-id", default=None, help="Paper ID selected by the user, e.g. arxiv_1.")
    parser.add_argument("--save-state", default="notebooks/output/latest_state.json", help="Where to save workflow state.")
    parser.add_argument("--interactive", action="store_true", help="Run with human-in-the-loop approval and clarification.")
    args = parser.parse_args()

    if args.interactive:
        run_interactive(args)
    else:
        run_once(args)


if __name__ == "__main__":
    main()
