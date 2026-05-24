import asyncio

from home_cluster_mcp.config import PrometheusSettings
from home_cluster_mcp.prometheus import PrometheusClient


def test_prometheus_query_disabled() -> None:
    result = asyncio.run(PrometheusClient(PrometheusSettings()).query("up"))

    assert result["enabled"] is False
    assert "not configured" in result["error"]
