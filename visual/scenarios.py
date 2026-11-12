"""Build the selectable case list.

Base cases are YAML files. Extra cases are composed at runtime from
``config/case_variants.json`` on top of the base scenario, so no near-duplicate
YAML files have to be kept in the repository.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from config.settings import BASE_DIR, CASES_DIR, SCENARIO_FILE_PATTERNS

VARIANT_CONFIG = BASE_DIR / "config" / "case_variants.json"


def _read_yaml(path: Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _title(data: Dict[str, Any], fallback: str) -> str:
    metadata = data.get("metadata")
    if isinstance(metadata, dict) and metadata.get("title"):
        return str(metadata["title"])
    return str(data.get("title") or fallback)


def source_from_path(path: Path) -> Dict[str, Any]:
    data = _read_yaml(path)
    return {
        "key": str(path),
        "title": _title(data, path.stem),
        "path": Path(path),
        "data": data,
        "kind": "file",
    }


def _variant_data(
    base: Dict[str, Any], variant: Dict[str, Any], config: Dict[str, Any]
) -> Dict[str, Any]:
    data = copy.deepcopy(base)
    data["metadata"] = {
        "case_id": variant.get("id", "variant"),
        "title": variant.get("title", variant.get("id", "Varian")),
        "description": variant.get("description", ""),
        "author": variant.get("author", config.get("default_author", "")),
        "group": variant.get("group", config.get("default_author", "")),
    }
    data["entities"] = copy.deepcopy(variant.get("entities", {}))
    plan = copy.deepcopy(base.get("execution_plan", {}))
    plan["events"] = copy.deepcopy(variant.get("events", []))
    for key in ("start_node", "goal_node", "algorithm"):
        if key in variant:
            plan[key] = variant[key]
    data["execution_plan"] = plan
    data["sample"] = {"note": variant.get("note", "")}
    return data


def load_scenario_sources() -> List[Dict[str, Any]]:
    """Return every selectable case, files first and runtime variants after."""
    sources: List[Dict[str, Any]] = []
    for pattern in SCENARIO_FILE_PATTERNS:
        for path in sorted(CASES_DIR.glob(pattern)):
            sources.append(source_from_path(path))

    if not VARIANT_CONFIG.exists():
        return sources
    try:
        config = json.loads(VARIANT_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return sources

    base_path = Path(config.get("base_scenario", ""))
    if not base_path.is_absolute():
        base_path = BASE_DIR / base_path
    if not base_path.exists():
        return sources
    base = _read_yaml(base_path)

    for variant in config.get("variants", []):
        variant_id = variant.get("id")
        if not variant_id:
            continue
        sources.append(
            {
                "key": f"variant:{variant_id}",
                "title": variant.get("title", variant_id),
                "path": base_path,
                "data": _variant_data(base, variant, config),
                "kind": "variant",
            }
        )
    return sources
