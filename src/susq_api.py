from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class SusqAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class APIConfig:
    base_url: str = os.getenv("SUSQ_API_BASE_URL", "https://sig.thesuper.market")
    api_key: str | None = os.getenv("SUSQ_API_KEY")
    prices_path: str = os.getenv("SUSQ_PRICES_PATH", "/api/v1/exchanges/prices")
    timeout_seconds: float = float(os.getenv("SUSQ_TIMEOUT", "15"))


class SusqAPI:
    """Thin v1 API transport.

    Endpoint/query shapes remain configurable until the authenticated API
    Reference is verified. Never hard-code a participant API key here.
    """

    def __init__(self, config: APIConfig | None = None) -> None:
        self.config = config or APIConfig()
        if not self.config.api_key:
            raise SusqAPIError(
                "SUSQ_API_KEY is missing. Set it in the local environment."
            )

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = urllib.parse.urlencode(
            {k: v for k, v in (params or {}).items() if v is not None},
            doseq=True,
        )
        url = self.config.base_url.rstrip("/") + "/" + path.lstrip("/")
        if query:
            url += "?" + query

        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
                "User-Agent": "susquehanna-predictions-cup/0.1",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise SusqAPIError(f"HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise SusqAPIError(f"Network error: {exc}") from exc

        if isinstance(data, dict) and "error" in data:
            error = data["error"]
            if isinstance(error, dict):
                raise SusqAPIError(
                    f"{error.get('code', 'API_ERROR')}: {error.get('message', 'unknown error')}"
                )
            raise SusqAPIError(str(error))
        return data

    def bulk_prices(self, exchange_ids: list[int | str]) -> Any:
        """Fetch a bulk price batch for up to 100 exchange IDs."""
        if not exchange_ids:
            return []
        if len(exchange_ids) > 100:
            raise ValueError("bulk_prices accepts at most 100 exchange IDs per call")
        param_name = os.getenv("SUSQ_PRICE_IDS_PARAM", "exchangeIds")
        return self.get(self.config.prices_path, {param_name: exchange_ids})
