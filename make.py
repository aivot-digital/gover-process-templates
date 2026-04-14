#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent
PROCESSES_DIR = ROOT_DIR / "processes"
NODES_DIR = ROOT_DIR / "nodes"
INDEX_PATH = ROOT_DIR / "index.json"


class IndexBuildError(RuntimeError):
    """Raised when an export file cannot be converted into an index entry."""


def load_json_file(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise IndexBuildError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise IndexBuildError(f"Expected top-level object in {path}")

    return data


def require_string(data: dict[str, Any], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise IndexBuildError(f"Missing or invalid string '{key}' in {path}")
    return value


def require_object(data: dict[str, Any], key: str, path: Path) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise IndexBuildError(f"Missing or invalid object '{key}' in {path}")
    return value


def metadata_path_for(export_path: Path) -> Path:
    return export_path.with_suffix(".meta.json")


def load_metadata_file(export_path: Path) -> tuple[Path, dict[str, Any]]:
    metadata_path = metadata_path_for(export_path)
    if not metadata_path.is_file():
        raise IndexBuildError(f"Missing metadata file for {export_path}: {metadata_path}")
    return metadata_path, load_json_file(metadata_path)


def to_index_path(path: Path) -> str:
    relative_path = path.relative_to(ROOT_DIR).as_posix()
    return f"./{relative_path}"


def iter_export_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.rglob("*.json")
        if path.is_file() and not path.name.endswith(".meta.json")
    )


def build_process_entry(path: Path) -> dict[str, str]:
    export_data = load_json_file(path)
    require_object(export_data, "process", path)
    metadata_path, metadata = load_metadata_file(path)

    return {
        "name": require_string(metadata, "name", metadata_path),
        "description": require_string(metadata, "description", metadata_path),
        "vendor": require_string(export_data, "createdByVendor", path),
        "path": to_index_path(path),
        "appVersion": require_string(export_data, "appVersion", path),
        "appBuildNumber": require_string(export_data, "appBuildNumber", path),
    }


def build_node_entry(path: Path) -> dict[str, str]:
    export_data = load_json_file(path)
    require_object(export_data, "node", path)
    metadata_path, metadata = load_metadata_file(path)

    return {
        "name": require_string(metadata, "name", metadata_path),
        "description": require_string(metadata, "description", metadata_path),
        "vendor": require_string(export_data, "createdByVendor", path),
        "path": to_index_path(path),
        "appVersion": require_string(export_data, "appVersion", path),
        "appBuildNumber": require_string(export_data, "appBuildNumber", path),
    }


def build_index() -> dict[str, list[dict[str, str]]]:
    processes = [build_process_entry(path) for path in iter_export_files(PROCESSES_DIR)]
    nodes = [build_node_entry(path) for path in iter_export_files(NODES_DIR)]

    return {
        "processes": sorted(processes, key=lambda entry: entry["path"]),
        "nodes": sorted(nodes, key=lambda entry: entry["path"]),
    }


def write_index_file(index_data: dict[str, list[dict[str, str]]]) -> None:
    with INDEX_PATH.open("w", encoding="utf-8") as handle:
        json.dump(index_data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main() -> int:
    index_data = build_index()
    write_index_file(index_data)
    print(f"Wrote {INDEX_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
