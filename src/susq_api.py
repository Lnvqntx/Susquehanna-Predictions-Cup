from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SusqAPIError(RuntimeError):
    """API error with the server's stable error code when available."""


def load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / '.env'
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding='utf-8').splitlines():
        raw = raw.strip()
        if not raw or raw.startswith('#') or '=' not in raw:
            continue
        key, value = raw.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


load_local_env()


@dataclass(frozen=True)
class APIConfig:
    base_url: str = os.getenv('SUSQ_API_BASE_URL', 'https://www.thesuper.market/api/v1')
    api_key: str | None = os.getenv('SUSQ_API_KEY')
    timeout_seconds: float = float(os.getenv('SUSQ_TIMEOUT', '15'))


class SusqAPI:
    def __init__(self, config: APIConfig | None = None) -> None:
        self.config = config or APIConfig()
        if not self.config.api_key:
            raise SusqAPIError('SUSQ_API_KEY is missing. Put it in the repo-local .env file.')

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None}, doseq=True)
        url = self.config.base_url.rstrip('/') + '/' + path.lstrip('/')
        if query:
            url += '?' + query
        request = urllib.request.Request(url, headers={'Accept':'application/json','Authorization':f'Bearer {self.config.api_key}','User-Agent':'susquehanna-predictions-cup/0.1'}, method='GET')
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read().decode('utf-8')
                data = json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            body = exc.read().decode('utf-8', errors='replace')
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = {}
            error = payload.get('error') if isinstance(payload, dict) else None
            if isinstance(error, dict):
                raise SusqAPIError(f"{error.get('code','API_ERROR')}: {error.get('message','unknown error')}") from exc
            raise SusqAPIError(f'HTTP {exc.code}: {body}') from exc
        except urllib.error.URLError as exc:
            raise SusqAPIError(f'Network error: {exc}') from exc
        return data

    def account(self) -> Any:
        return self.get('/account')

    def list_tournaments(self, status: str = 'active', limit: int = 100) -> Any:
        return self.get('/tournaments', {'status': status, 'limit': max(1, min(100, limit))})

    def tournament(self, slug: str) -> Any:
        return self.get(f"/tournaments/{urllib.parse.quote(slug, safe='')}")

    def list_tournament_markets(self, slug: str, status: str = 'open', limit: int = 100, cursor: str | None = None, search: str | None = None) -> Any:
        return self.get(f"/tournaments/{urllib.parse.quote(slug, safe='')}/markets", {'status': status, 'limit': max(1, min(100, limit)), 'cursor': cursor, 'search': search})

    def list_all_tournament_markets(self, slug: str, status: str = 'open') -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            payload = self.list_tournament_markets(slug, status=status, limit=100, cursor=cursor)
            rows.extend(payload.get('data', []))
            pagination = payload.get('pagination', {})
            if not pagination.get('hasMore'):
                return rows
            cursor = pagination.get('nextCursor')
            if not cursor:
                raise SusqAPIError('API reported hasMore=true but returned no nextCursor.')

    def price(self, exchange_id: str, tournament_id: str | None = None) -> Any:
        return self.get(f"/exchanges/{urllib.parse.quote(str(exchange_id), safe='')}/price", {'tournamentId': tournament_id})

    def orderbook(self, exchange_id: str, depth: int = 20, tournament_id: str | None = None) -> Any:
        return self.get(f"/exchanges/{urllib.parse.quote(str(exchange_id), safe='')}/orderbook", {'depth': max(1, min(200, depth)), 'tournamentId': tournament_id})

    def bulk_prices(self, exchange_ids: list[str | int], tournament_id: str | None = None) -> list[dict[str, Any]]:
        ids = [str(x) for x in exchange_ids if str(x).strip()]
        results: list[dict[str, Any]] = []
        for start in range(0, len(ids), 100):
            chunk = ids[start:start+100]
            payload = self.get('/exchanges/prices', {'ids': ','.join(chunk), 'tournamentId': tournament_id})
            results.extend(payload.get('data', []))
        return results
