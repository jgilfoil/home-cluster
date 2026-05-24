from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .config import Settings, load_settings
from .git_hint import resource_git_hint as find_resource_git_hint
from .kube import KubernetesClient
from .prometheus import PrometheusClient


def create_server(settings: Settings | None = None) -> Any:
    from mcp.server.fastmcp import FastMCP

    resolved_settings = settings or load_settings()
    kube = KubernetesClient(resolved_settings)
    prometheus = PrometheusClient(resolved_settings.prometheus)

    mcp = FastMCP("home-cluster", json_response=True)

    @mcp.tool()
    def cluster_overview() -> dict[str, Any]:
        """Summarize node, namespace, pod, and workload health."""

        return kube.cluster_overview()

    @mcp.tool()
    def flux_status() -> dict[str, Any]:
        """Summarize Flux Kustomization, HelmRelease, and Source readiness."""

        return kube.flux_status()

    @mcp.tool()
    def recent_events(
        namespace: str | None = None,
        involved_kind: str | None = None,
        involved_name: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Return recent Kubernetes events, optionally filtered by object."""

        return kube.recent_events(namespace, involved_kind, involved_name, limit)

    @mcp.tool()
    def workload_status(namespace: str | None = None) -> dict[str, Any]:
        """Return readiness and restart summaries for common workload resources."""

        return kube.workload_status(namespace)

    @mcp.tool()
    def pod_summary(namespace: str, name: str) -> dict[str, Any]:
        """Return pod conditions, container state, refs, mounts, probes, and events."""

        return kube.pod_summary(namespace, name)

    @mcp.tool()
    def pod_logs(
        namespace: str,
        name: str,
        container: str | None = None,
        previous: bool = False,
        tail_lines: int | None = None,
    ) -> dict[str, Any]:
        """Return bounded, redacted pod logs."""

        return kube.pod_logs(namespace, name, container, previous, tail_lines)

    @mcp.tool()
    def resource_git_hint(kind: str, name: str, namespace: str | None = None) -> dict[str, Any]:
        """Find likely Git manifests for a live Kubernetes resource."""

        return find_resource_git_hint(resolved_settings.repo_root, kind, name, namespace)

    @mcp.tool()
    async def prometheus_query(query: str, time: str | None = None) -> dict[str, Any]:
        """Run a read-only Prometheus instant query when a Prometheus URL is configured."""

        return await prometheus.query(query, time)

    @mcp.tool()
    def pod_exec_plan(namespace: str, argv: list[str]) -> dict[str, Any]:
        """Classify a proposed non-interactive pod exec command without running it."""

        return kube.pod_exec_plan(namespace, argv)

    @mcp.tool()
    def pod_exec(
        namespace: str,
        pod: str,
        argv: list[str],
        container: str | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """Run an approved, non-interactive, classified diagnostic command in a pod."""

        result = kube.pod_exec(namespace, pod, container, argv, reason)
        if result.get("executed"):
            print(json.dumps({"pod_exec_audit": result.get("audit")}), file=sys.stderr, flush=True)
        return result

    return mcp


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the home-cluster MCP stdio server")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to the home-cluster MCP YAML config",
    )
    args = parser.parse_args(argv)
    settings = load_settings(args.config)
    server = create_server(settings)
    server.run()


if __name__ == "__main__":
    main()
