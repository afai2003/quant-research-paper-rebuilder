from __future__ import annotations

import argparse
import json
from pathlib import Path

from .graph import build_graph
from .agents import business_analyst_node,filter_paper_node, read_paper_node


def ask_yes_no(prompt: str) -> bool:
    while True:
        answer = input(f"{prompt} [y/n]: ").strip().lower()

        if answer in ["y", "yes"]:
            return True

        if answer in ["n", "no"]:
            return False

        print("Please enter y or n.")


def ask_text(prompt: str) -> str:
    return input(f"{prompt}: ").strip()


def print_scope(result: dict) -> None:
    print("\n=== PROPOSED RESEARCH SCOPE ===")

    scope = result.get("scope", {})


    print(f"Scope: {scope}")

    if result.get("ba_message"):
        print("\nBA Message:")
        print(result["ba_message"])

    if result.get("ba_questions"):
        print("\nBA Questions:")
        for q in result["ba_questions"]:
            print(f"- {q}")


def print_top_papers(result: dict) -> None:
    print("\n=== SELECTED PAPERS ===")

    selected_papers = result.get("top_papers", [])

    if not selected_papers:
        print("No selected papers found.")
        return

    for p in selected_papers:
        print("\n" + "-" * 80)

        print(f"Paper ID: {p.get('paper_id')}")
        print(f"Title: {p.get('title')}")
        print(f"arXiv ID: {p.get('arxiv_id')}")
        print(f"Link: {p.get('link')}")

        authors = p.get("authors", [])
        if isinstance(authors, list):
            authors = ", ".join(authors)
        print(f"Authors: {authors}")

        print(f"Published Date: {p.get('published_date')}")

        categories = p.get("arxiv_categories", [])
        if isinstance(categories, list):
            categories = ", ".join(categories)
        print(f"arXiv Categories: {categories}")

        print(f"Brief Summary: {p.get('brief_summary')}")
        print(f"Scope Relevance Score: {p.get('scope_relevance_score')}")
        print(f"Why Relevant to Scope: {p.get('why_relevant_to_scope')}")
        print(f"Evidence from Brief Summary: {p.get('evidence_from_brief_summary')}")
        print(f"Possible Data Needed: {p.get('possible_data_needed')}")
        print(f"Required Tools or Methods: {p.get('required_tools_or_methods')}")
        print(f"Rebuild Difficulty: {p.get('rebuild_difficulty')}")
        print(f"Rebuild Chance: {p.get('rebuild_chance')}")
        print(f"Reason for Rebuild Chance: {p.get('reason_for_rebuild_chance')}")


def save_state(result: dict, save_path: str) -> None:
    path = Path(save_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nState saved to: {path}")


def run_interactive(args) -> None:

    query = args.query
    selected_paper_id = args.selected_paper_id

    # --------------------------------------------------
    # Step 1: BA shapes scope
    # --------------------------------------------------

    clarification_history = []

    ba_state = {
        "user_query": query,
        "clarification_history": clarification_history,
    }

    while True:

        result = business_analyst_node(ba_state)

        print_scope(result)

        ba_output = result.get("ba_output", result)

        scope_clear = ba_output.get("scope_clear", False)

        if scope_clear:
            print("\n=== PROPOSED FINAL SCOPE ===")

            final_scope = json.dumps(
                ba_output.get("scope", {}),
                indent=2,
                ensure_ascii=False,
            )

            print(final_scope)

            approved = ask_yes_no("\nDo you approve this scope?")

            if approved:
                print("\nScope approved. Proceeding to filter paper...")
                break

            # --------------------------------------------------
            # User does not approve, collect feedback
            # --------------------------------------------------

            user_feedback = ask_text("\nWhat would you like to change in the scope")

            clarification_history.append(
                {
                    "question": "User rejected the proposed scope. What changes should be made?",
                    "answer": user_feedback,
                }
            )

            query = f"""
                    Original user query:
                    {args.query}

                    Previously proposed scope:
                    {final_scope}

                    User feedback on proposed scope:
                    {user_feedback}

                    Clarification history:
                    {json.dumps(clarification_history, ensure_ascii=False, indent=2)}
                    """

            ba_state = {
                "user_query": query,
                "clarification_history": clarification_history,
            }

            continue

        next_question = ba_output.get("next_question")

        if not next_question:
            print("\nBA says scope is unclear, but no next question was returned.")
            print("Workflow stopped.")
            save_state(result, args.save_state)
            return

        print("\nBA needs clarification:")
        print(next_question)

        user_answer = ask_text("\nYour answer")

        clarification_history.append(
            {
                "question": next_question,
                "answer": user_answer,
            }
        )

        query = f"""
                Original user query:
                {args.query}

                Clarification history:
                {json.dumps(clarification_history, ensure_ascii=False, indent=2)}
                """

        ba_state = {
            "user_query": query,
            "clarification_history": clarification_history,
        }

    # --------------------------------------------------
    # Step 2: Run filtering papers
    # --------------------------------------------------
    paper_state = {"scope": final_scope}
    result  = filter_paper_node(paper_state)


    

    print_top_papers(result)

    if result.get("all_papers_low_chance"):
        print("\nAll papers have low reproducibility chance.")
        print("The workflow should return to BA to discuss with user.")
        save_state(result, args.save_state)
        return

    print("====== End of paper filtering ======")

    # --------------------------------------------------
    # Step 3: Ask user to select paper
    # --------------------------------------------------
    if not selected_paper_id:
        selected_paper_id = ask_text("\nPlease choose a paper_id to rebuild, e.g. paper_1")



    # --------------------------------------------------
    # Step 4: read paper and wirte code
    # --------------------------------------------------
    notebook_app = build_graph()

    graph_state = {
        "selected_paper_id": selected_paper_id,
        "top_papers": result.get("top_papers", []),
        "revision_count": 0,
        "logs": [],
    }

    final_state = {}

    for mode, chunk in notebook_app.stream(
        graph_state,
        {"recursion_limit": 20},
        stream_mode=["custom", "updates", "values"],
    ):
        # --------------------------------------------------
        # Custom logs from monitor.py / get_stream_writer()
        # --------------------------------------------------
        if mode == "custom":
            print(
                f"[{chunk.get('time')}] "
                f"{chunk.get('node')} | "
                f"{chunk.get('event')} | "
                f"{chunk.get('message')}"
            )

        # --------------------------------------------------
        # Node-level state update
        # --------------------------------------------------
        elif mode == "updates":
            for node_name, update in chunk.items():
                print(f"\n--- Node finished: {node_name} ---")
                print("Updated keys:", list(update.keys()))

        # --------------------------------------------------
        # Full state after each step
        # We keep overwriting final_state,
        # so after the loop it becomes the final graph output.
        # --------------------------------------------------
        elif mode == "values":
            final_state = chunk


    notebook_result = final_state

    result = {
        **result,
        **notebook_result,
    }

    print("\nNotebook workflow completed.")
    print(f"Status: {result.get('status')}")
    print(f"Notebook path: {result.get('notebook_path')}")

    # # --------------------------------------------------
    # # Final result
    # # --------------------------------------------------
    # print("\n=== WORKFLOW COMPLETED ===")
    # print(f"Status: {result.get('status')}")

    # if result.get("final_notebook_path"):
    #     print(f"Final notebook: {result.get('final_notebook_path')}")

    # save_state(result, args.save_state)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Quant Research Paper Rebuilding Agent workflow."
    )

    parser.add_argument(
        "--query",
        required=True,
        help="User's quantitative research idea.",
    )

    parser.add_argument(
        "--selected-paper-id",
        default=None,
        help="Paper ID selected by the user, e.g. paper_1.",
    )

    parser.add_argument(
        "--data-path",
        default=None,
        help="Path to user-provided data file.",
    )

    parser.add_argument(
        "--save-state",
        default="notebooks/output/latest_state.json",
        help="Where to save workflow state.",
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run workflow in interactive human-in-the-loop mode.",
    )

    args = parser.parse_args()

    if args.interactive:
        run_interactive(args)
    else:
        app = build_ba_graph()

        init_state = {
            "user_query": args.query,
            "selected_paper_id": args.selected_paper_id,
            "data_path": args.data_path,
        }

        result = app.invoke(init_state, {"recursion_limit": 20})

        print("\n=== WORKFLOW STATUS ===")
        print(result.get("status"))

        save_state(result, args.save_state)


if __name__ == "__main__":
    main()