from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any

import certifi

BASE = "https://www.pollingforecast.com/api/us"


class PollingForecastError(RuntimeError):
    pass


def _get(path: str) -> dict[str, Any]:
    req = urllib.request.Request(
        BASE + path,
        headers={"Accept": "application/json", "User-Agent": "susquehanna-predictions-cup/0.1"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(
            req,
            timeout=15,
            context=ssl.create_default_context(cafile=certifi.where()),
        ) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        raise PollingForecastError(f"Polling Forecast request failed: {exc}") from exc


def fetch_forecasts() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for office in ("house", "senate", "governors"):
        payload = _get(f"/{office}")
        for row in payload.get("rows", []):
            out[str(row.get("key"))] = {**row, "office": office}
    return out


def party_probability(row: dict[str, Any], party: str) -> float | None:
    party = party.lower()
    if party == "democratic":
        value = row.get("chance_left")
    elif party == "republican":
        value = row.get("chance_right")
        if value is None and row.get("chance_left") is not None:
            value = 1.0 - float(row["chance_left"])
    else:
        return None
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
