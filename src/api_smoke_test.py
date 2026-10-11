from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.susq_api import SusqAPI, SusqAPIError


def main() -> int:
    try:
        account = SusqAPI().account()
    except SusqAPIError as exc:
        print(f'❌ API check failed: {exc}')
        return 2
    print('✅ API authentication works')
    print(f"   account_id={account.get('id')}")
    print(f"   username={account.get('username')}")
    print(f"   default_balance={account.get('balance')}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())