from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def resource_git_hint(
    repo_root: Path,
    kind: str,
    name: str,
    namespace: str | None = None,
    max_matches: int = 20,
) -> dict[str, Any]:
    exact: list[dict[str, Any]] = []
    fuzzy: list[str] = []
    search_roots = [repo_root / "kubernetes" / "apps", repo_root / "kubernetes" / "flux"]

    for root in search_roots:
        if not root.exists():
            continue
        for path in sorted(list(root.rglob("*.yaml")) + list(root.rglob("*.yml"))):
            if ".sops." in path.name:
                continue
            rel = str(path.relative_to(repo_root))
            if name in path.parts or name in path.name:
                fuzzy.append(rel)
            exact.extend(_matching_documents(path, kind, name, namespace, repo_root))
            if len(exact) >= max_matches:
                break

    return {
        "query": {"kind": kind, "name": name, "namespace": namespace},
        "exact_matches": exact[:max_matches],
        "fuzzy_paths": sorted(set(fuzzy))[:max_matches],
    }


def _matching_documents(
    path: Path,
    kind: str,
    name: str,
    namespace: str | None,
    repo_root: Path,
) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            docs = list(yaml.safe_load_all(handle))
    except yaml.YAMLError:
        return []

    matches = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        metadata = doc.get("metadata") or {}
        if doc.get("kind") != kind or metadata.get("name") != name:
            continue
        doc_namespace = metadata.get("namespace")
        if namespace and doc_namespace and doc_namespace != namespace:
            continue
        matches.append(
            {
                "path": str(path.relative_to(repo_root)),
                "apiVersion": doc.get("apiVersion"),
                "kind": doc.get("kind"),
                "name": metadata.get("name"),
                "namespace": doc_namespace,
            }
        )
    return matches
