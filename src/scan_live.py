from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.susq_api import SusqAPI, SusqAPIError


def load_ids(path: Path) -> list[str]:
    values: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw and not raw.startswith("#"):
            values.append(raw)
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch a live Susquehanna price batch.")
    parser.add_argument("--ids", default="data/exchange_ids.txt")
    parser.add_argument("--out", default="data/live_prices.json")
    args = parser.parse_args()

    ids = load_ids(Path(args.ids))
    try:
        payload = SusqAPI().bulk_prices(ids)
    except (SusqAPIError, ValueError) as exc:
        print(f"API error: {exc}")
        return 2

    Path(args.out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Fetched {len(ids)} exchange IDs -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
