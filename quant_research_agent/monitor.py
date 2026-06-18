from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from langgraph.config import get_stream_writer


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_stream(event: dict[str, Any]) -> None:
    """Send live logs when LangGraph is running in custom stream mode."""
    try:
        writer = get_stream_writer()
        writer(event)
    except Exception:
        # Running without stream_mode="custom" is valid.
        return


def monitor_node(node_name: str, node_func: Callable[[dict[str, Any]], dict[str, Any]]):
    """Wrap a graph node with start/end/error log events."""

    def wrapped_node(state: dict[str, Any]) -> dict[str, Any]:
        start_log = {
            "time": now(),
            "node": node_name,
            "event": "start",
            "message": f"Starting {node_name}",
        }
        safe_stream(start_log)

        try:
            result = node_func(state) or {}
            end_log = {
                "time": now(),
                "node": node_name,
                "event": "end",
                "message": f"Finished {node_name}",
                "output_keys": list(result.keys()),
            }
            safe_stream(end_log)
            return {**result, "logs": [start_log, end_log]}

        except Exception as exc:  # fail gracefully inside graph state
            error_log = {
                "time": now(),
                "node": node_name,
                "event": "error",
                "message": str(exc),
            }
            safe_stream(error_log)
            return {
                "status": "error",
                "logs": [start_log, error_log],
                "error_message": str(exc),
            }

    return wrapped_node
