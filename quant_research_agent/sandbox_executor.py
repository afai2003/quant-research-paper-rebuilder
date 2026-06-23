# quant_research_agent/sandbox_executor.py

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError


def run_notebook_sandbox(
    notebook_path: str,
    output_path: str = "notebooks/output/executed_quant_research_notebook.ipynb",
    timeout: int = 300,
) -> dict[str, Any]:
    """
    Execute a generated notebook from top to bottom.

    This version runs in the current Python environment.
    It is not a full Docker sandbox yet, but it is the best first integration
    for your current LangGraph project.
    """
    notebook_path_obj = Path(notebook_path)
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    try:
        if not notebook_path_obj.exists():
            return {
                "sandbox_passed": False,
                "stage": "file_check",
                "error_type": "FileNotFoundError",
                "error_message": f"Notebook not found: {notebook_path}",
            }

        with notebook_path_obj.open("r", encoding="utf-8") as f:
            nb = nbformat.read(f, as_version=4)

        nbformat.validate(nb)

        client = NotebookClient(
            nb,
            timeout=timeout,
            kernel_name="python3",
            allow_errors=False,
        )
        client.execute()

        with output_path_obj.open("w", encoding="utf-8") as f:
            nbformat.write(nb, f)

        return {
            "sandbox_passed": True,
            "stage": "execution",
            "input_notebook": str(notebook_path_obj),
            "executed_notebook": str(output_path_obj),
            "error_type": None,
            "error_message": None,
        }

    except CellExecutionError as exc:
        return {
            "sandbox_passed": False,
            "stage": "cell_execution",
            "input_notebook": str(notebook_path_obj),
            "error_type": "CellExecutionError",
            "error_message": str(exc),
            "traceback": traceback.format_exc(),
        }

    except Exception as exc:
        return {
            "sandbox_passed": False,
            "stage": "unknown",
            "input_notebook": str(notebook_path_obj),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": traceback.format_exc(),
        }