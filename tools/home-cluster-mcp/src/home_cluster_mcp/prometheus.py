from __future__ import annotations

from typing import Any

from .config import PrometheusSettings
from .redaction import redact_value


class PrometheusClient:
    def __init__(self, settings: PrometheusSettings) -> None:
        self.settings = settings

    async def query(self, query: str, time: str | None = None) -> dict[str, Any]:
        if not self.settings.enabled:
            return {"enabled": False, "error": "Prometheus URL is not configured"}
        if not query.strip():
            raise ValueError("Prometheus query cannot be empty")

        import httpx

        params: dict[str, str] = {"query": query}
        if time:
            params["time"] = time

        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
            response = await client.get(f"{self.settings.url.rstrip('/')}/api/v1/query", params=params)
            response.raise_for_status()
            payload = response.json()
        return redact_value({"enabled": True, "response": payload})
