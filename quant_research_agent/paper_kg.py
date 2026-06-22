from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def split_paper_text(
    paper_text: str,
    max_chars: int = 3500,
    overlap_chars: int = 300,
) -> list[dict[str, Any]]:
    """Split extracted PDF text into page-aware chunks."""
    page_blocks = re.split(r"\n\s*--- Page (\d+) ---\s*\n", paper_text)

    chunks: list[dict[str, Any]] = []
    chunk_no = 1

    # page_blocks format: ["", "1", "page text", "2", "page text", ...]
    for i in range(1, len(page_blocks), 2):
        page_no = int(page_blocks[i])
        page_text = page_blocks[i + 1].strip()

        start = 0
        while start < len(page_text):
            end = start + max_chars
            text = page_text[start:end].strip()

            if text:
                chunks.append(
                    {
                        "chunk_id": f"page_{page_no}_chunk_{chunk_no}",
                        "page": page_no,
                        "text": text,
                    }
                )
                chunk_no += 1

            if end >= len(page_text):
                break

            start = max(0, end - overlap_chars)

    return chunks


def normalize_node_key(node_type: str, label: str) -> str:
    """Create a stable key for duplicate merging."""
    raw = f"{node_type}:{label}".lower()
    raw = re.sub(r"[^a-z0-9]+", "_", raw)
    return raw.strip("_")


def merge_graph_fragments(fragments: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge chunk-level graph fragments into one paper knowledge graph."""
    nodes_by_key: dict[str, dict[str, Any]] = {}
    edges_seen: set[tuple[str, str, str]] = set()
    edges: list[dict[str, Any]] = []
    implementation_steps: list[dict[str, Any]] = []
    issues: list[str] = []

    for fragment in fragments:
        chunk_id = fragment.get("chunk_id")
        page = fragment.get("page")

        for node in fragment.get("nodes", []):
            node_type = str(node.get("type", "Concept")).strip()
            label = str(node.get("label", "")).strip()

            if not label:
                continue

            key = normalize_node_key(node_type, label)

            if key not in nodes_by_key:
                nodes_by_key[key] = {
                    "node_id": key,
                    "type": node_type,
                    "label": label,
                    "description": node.get("description", ""),
                    "evidence": [],
                }

            evidence_quote = node.get("evidence_quote", "")
            if evidence_quote:
                nodes_by_key[key]["evidence"].append(
                    {
                        "chunk_id": chunk_id,
                        "page": page,
                        "quote": evidence_quote,
                    }
                )

        for edge in fragment.get("edges", []):
            source_type = str(edge.get("source_type", "Concept")).strip()
            source_label = str(edge.get("source_label", "")).strip()
            target_type = str(edge.get("target_type", "Concept")).strip()
            target_label = str(edge.get("target_label", "")).strip()
            relation = str(edge.get("relation", "RELATED_TO")).strip().upper()

            if not source_label or not target_label:
                continue

            source_id = normalize_node_key(source_type, source_label)
            target_id = normalize_node_key(target_type, target_label)
            edge_key = (source_id, relation, target_id)

            if edge_key in edges_seen:
                continue

            edges_seen.add(edge_key)
            edges.append(
                {
                    "source": source_id,
                    "target": target_id,
                    "relation": relation,
                    "evidence": [
                        {
                            "chunk_id": chunk_id,
                            "page": page,
                            "quote": edge.get("evidence_quote", ""),
                        }
                    ],
                }
            )

        for step in fragment.get("implementation_steps", []):
            implementation_steps.append(
                {
                    **step,
                    "chunk_id": chunk_id,
                    "page": page,
                }
            )

        issues.extend(fragment.get("missing_or_unclear", []))

    return {
        "nodes": list(nodes_by_key.values()),
        "edges": edges,
        "implementation_steps": implementation_steps,
        "missing_or_unclear": issues,
    }


def graph_to_context(paper_graph: dict[str, Any], max_nodes: int = 80, max_edges: int = 120) -> str:
    """Convert the paper graph into compact text for the notebook writer."""
    lines = []

    lines.append("## Important nodes")
    for node in paper_graph.get("nodes", [])[:max_nodes]:
        lines.append(
            f"- [{node.get('type')}] {node.get('label')}: {node.get('description', '')}"
        )

    lines.append("\n## Important edges")
    node_map = {node["node_id"]: node for node in paper_graph.get("nodes", [])}

    for edge in paper_graph.get("edges", [])[:max_edges]:
        source = node_map.get(edge.get("source"), {}).get("label", edge.get("source"))
        target = node_map.get(edge.get("target"), {}).get("label", edge.get("target"))
        relation = edge.get("relation")
        lines.append(f"- {source} --{relation}--> {target}")

    lines.append("\n## Implementation steps")
    for step in paper_graph.get("implementation_steps", []):
        lines.append(f"- {step.get('description', step)}")

    lines.append("\n## Missing or unclear")
    for issue in paper_graph.get("missing_or_unclear", []):
        lines.append(f"- {issue}")

    return "\n".join(lines)


def save_paper_graph(
    paper_graph: dict[str, Any],
    paper_id: str,
    output_dir: str = "outputs/paper_graph",
) -> str:
    """Save paper graph as JSON."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    out_path = path / f"{paper_id}_graph.json"
    out_path.write_text(
        json.dumps(paper_graph, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return str(out_path)