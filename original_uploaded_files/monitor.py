from datetime import datetime

from langgraph.config import get_stream_writer


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_stream(event: dict):
    """
    Send live log if graph is running with stream_mode='custom'.
    If not streaming, skip silently.
    """
    try:
        writer = get_stream_writer()
        writer(event)
    except Exception:
        pass


def monitor_node(node_name, node_func):
    def wrapped_node(state):
        start_log = {
            "time": now(),
            "node": node_name,
            "event": "start",
            "message": f"Starting {node_name}",
        }

        safe_stream(start_log)

        try:
            result = node_func(state)

            if result is None:
                result = {}

            end_log = {
                "time": now(),
                "node": node_name,
                "event": "end",
                "message": f"Finished {node_name}",
                "output_keys": list(result.keys()),
            }

            safe_stream(end_log)

            return {
                **result,
                "logs": [start_log, end_log],
            }

        except Exception as e:
            error_log = {
                "time": now(),
                "node": node_name,
                "event": "error",
                "message": str(e),
            }

            safe_stream(error_log)

            return {
                "status": "error",
                "logs": [start_log, error_log],
                "error_message": str(e),
            }

    return wrapped_node