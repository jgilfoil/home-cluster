from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_DENIED_NAMESPACES = {
    "cert-manager",
    "database",
    "flux-system",
    "kube-node-lease",
    "kube-public",
    "kube-system",
    "network",
    "observability",
    "rook-ceph",
    "storage",
}

DEFAULT_ALLOWED_EXEC_NAMESPACES = {
    "default",
    "media",
    "mymindinai",
    "mymindinai-dev",
}


@dataclass(frozen=True)
class Limits:
    log_tail_default: int = 100
    log_tail_max: int = 200
    event_max: int = 100
    exec_timeout_seconds: int = 10
    output_max_bytes: int = 32768

    def __post_init__(self) -> None:
        for name in (
            "log_tail_default",
            "log_tail_max",
            "event_max",
            "exec_timeout_seconds",
            "output_max_bytes",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or value <= 0:
                raise ValueError(f"limits.{name} must be a positive integer")
        if self.log_tail_default > self.log_tail_max:
            raise ValueError("limits.log_tail_default cannot exceed limits.log_tail_max")

    def clamp_log_tail(self, tail_lines: int | None) -> int:
        if tail_lines is None:
            return self.log_tail_default
        return max(1, min(int(tail_lines), self.log_tail_max))


@dataclass(frozen=True)
class ExecSettings:
    allowed_namespaces: frozenset[str] = field(
        default_factory=lambda: frozenset(DEFAULT_ALLOWED_EXEC_NAMESPACES)
    )
    denied_namespaces: frozenset[str] = field(
        default_factory=lambda: frozenset(DEFAULT_DENIED_NAMESPACES)
    )

    def is_allowed_namespace(self, namespace: str) -> bool:
        return namespace in self.allowed_namespaces and namespace not in self.denied_namespaces


@dataclass(frozen=True)
class PrometheusSettings:
    url: str | None = None
    timeout_seconds: int = 10

    @property
    def enabled(self) -> bool:
        return bool(self.url)


@dataclass(frozen=True)
class Settings:
    kubeconfig: Path
    repo_root: Path
    exec: ExecSettings = field(default_factory=ExecSettings)
    limits: Limits = field(default_factory=Limits)
    prometheus: PrometheusSettings = field(default_factory=PrometheusSettings)


def load_settings(config_path: str | Path | None = None) -> Settings:
    resolved_config = Path(
        config_path
        or os.environ.get("HOME_CLUSTER_MCP_CONFIG")
        or "tools/home-cluster-mcp/config.sample.yaml"
    )
    raw = _load_yaml(resolved_config)
    config_base = resolved_config.resolve().parent

    repo_root = _resolve_path(raw.get("repo_root", "."), config_base)
    kubeconfig = _resolve_path(raw.get("kubeconfig", ".private/codex-mcp/kubeconfig"), repo_root)

    exec_raw = raw.get("exec") or {}
    limits_raw = raw.get("limits") or {}
    prometheus_raw = raw.get("prometheus") or {}

    prometheus_url = os.environ.get("HOME_CLUSTER_MCP_PROMETHEUS_URL") or prometheus_raw.get("url")

    return Settings(
        kubeconfig=kubeconfig,
        repo_root=repo_root,
        exec=ExecSettings(
            allowed_namespaces=frozenset(
                _string_list(exec_raw.get("allowed_namespaces"), DEFAULT_ALLOWED_EXEC_NAMESPACES)
            ),
            denied_namespaces=frozenset(
                _string_list(exec_raw.get("denied_namespaces"), DEFAULT_DENIED_NAMESPACES)
            ),
        ),
        limits=Limits(
            log_tail_default=int(limits_raw.get("log_tail_default", 100)),
            log_tail_max=int(limits_raw.get("log_tail_max", 200)),
            event_max=int(limits_raw.get("event_max", 100)),
            exec_timeout_seconds=int(limits_raw.get("exec_timeout_seconds", 10)),
            output_max_bytes=int(limits_raw.get("output_max_bytes", 32768)),
        ),
        prometheus=PrometheusSettings(
            url=prometheus_url,
            timeout_seconds=int(prometheus_raw.get("timeout_seconds", 10)),
        ),
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"MCP config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("MCP config must be a YAML mapping")
    return data


def _resolve_path(value: str | os.PathLike[str], base: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _string_list(value: Any, default: set[str]) -> list[str]:
    if value is None:
        return sorted(default)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("expected a list of strings")
    return value
