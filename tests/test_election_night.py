import argparse
from datetime import datetime, timezone

import src.election_night as en


class FakeAPI:
    def __init__(self, books, positions, balance=10_000):
        self.books, self.positions, self.balance = books, positions, balance
        self.orders = []

    def orderbook(self, ex, depth=50, tournament_id=None):
        return self.books[ex]

    def tournament_positions(self, slug):
        return [{"exchangeId": k, "quantity": v} for k, v in self.positions.items()]

    def tournament(self, slug):
        return {"myBalance": self.balance}

    def place_order(self, **kw):
        self.orders.append(kw)
        return {"quantityTraded": kw["quantity"], "open": False}


ROWS = [
    {"race": "PA-08 House race", "party": "Republican", "poly_market_id": "R8", "susq_exchange": "927",
     "poly_yes_2026_10_29": "0.12"},
    {"race": "PA-08 House race", "party": "Democratic", "poly_market_id": "D8", "susq_exchange": "926",
     "poly_yes_2026_10_29": "0.87"},
    {"race": "Colorado Senate", "party": "Democratic", "poly_market_id": "COD", "susq_exchange": "945",
     "poly_yes_2026_10_29": "0.99"},
]


def args(**over):
    a = argparse.Namespace(live=True, interval=20, win_bid=0.96, confirm_secs=90, baseline_max=0.90,
                           max_buy=0.93, max_poly_spread=0.03, min_gap=0.04, per_race=2500, max_total=40_000, cash_floor=200,
                           lose_bid=0.03, min_dump_bid=0.02, recycle_bid=0.985,
                           start_dt=datetime(2020, 1, 1, tzinfo=timezone.utc))
    for k, v in over.items():
        setattr(a, k, v)
    return a


def run(monkeypatch, api, quotes, st, t, a=None):
    monkeypatch.setattr(en, "poly_quotes", lambda ids: quotes)
    monkeypatch.setattr(en, "save_state", lambda s: None)
    monkeypatch.setattr(en, "now", lambda: datetime.fromtimestamp(1_900_000_000 + t, tz=timezone.utc))
    en.cycle(api, {"id": "T", "slug": "s"}, ROWS, st, a or args())


def fresh():
    return {"baseline": {}, "first_seen_win": {}, "bought": {}, "dumped": [], "recycled": [], "spent": 0.0}


def q(bid, ask, closed=False, yes=None):
    return {"bid": bid, "ask": ask, "last": bid, "yes": yes if yes is not None else bid,
            "closed": closed, "yes_won": closed and (yes or 0) >= 0.99, "yes_lost": closed and (yes or 1) <= 0.01}


BOOKS = {
    "926": {"asks": [{"price": 0.88, "quantity": 2000}, {"price": 0.95, "quantity": 9000}],
            "bids": [{"price": 0.86, "quantity": 5000}]},
    "927": {"asks": [{"price": 0.14, "quantity": 9000}],
            "bids": [{"price": 0.11, "quantity": 3000}, {"price": 0.08, "quantity": 9000}]},
    "945": {"asks": [{"price": 0.90, "quantity": 9000}], "bids": [{"price": 0.89, "quantity": 9000}]},
}


def test_needs_confirmation_then_buys_called_winner_and_dumps_loser(monkeypatch):
    api = FakeAPI(BOOKS, {"927": 7993})
    st = fresh()
    quotes = {"D8": q(0.975, 0.98), "R8": q(0.02, 0.025), "COD": q(0.995, 0.997)}
    run(monkeypatch, api, quotes, st, 1_000)
    # loser dumped immediately, winner waits for confirmation, safe seat never bought
    assert [o["action"] for o in api.orders] == ["sell"]
    assert api.orders[0]["exchange_id"] == "927" and api.orders[0]["quantity"] == 7993
    run(monkeypatch, api, quotes, st, 1_100)
    buys = [o for o in api.orders if o["action"] == "buy"]
    assert len(buys) == 1 and buys[0]["exchange_id"] == "926"
    assert buys[0]["price"] <= 0.93                      # capped by max_buy / poly - gap
    assert "PA-08 House race|Democratic" in st["bought"]
    run(monkeypatch, api, quotes, st, 1_300)             # never buys the same race twice
    assert len([o for o in api.orders if o["action"] == "buy"]) == 1


def test_fading_signal_resets_and_dry_run_sends_nothing(monkeypatch):
    api = FakeAPI(BOOKS, {})
    st = fresh()
    run(monkeypatch, api, {"D8": q(0.97, 0.98)}, st, 1_000, args(live=False))
    run(monkeypatch, api, {"D8": q(0.80, 0.82)}, st, 1_050, args(live=False))
    assert "PA-08 House race|Democratic" not in st["first_seen_win"]
    run(monkeypatch, api, {"D8": q(0.97, 0.98)}, st, 1_100, args(live=False))
    run(monkeypatch, api, {"D8": q(0.97, 0.98)}, st, 1_150, args(live=False))
    assert st["bought"] == {} and api.orders == []      # clock restarted at 1_100
    run(monkeypatch, api, {"D8": q(0.97, 0.98)}, st, 1_200, args(live=False))
    assert "PA-08 House race|Democratic" in st["bought"] and api.orders == []


def test_nothing_before_start(monkeypatch):
    api = FakeAPI(BOOKS, {"927": 100})
    st = fresh()
    a = args(start_dt=datetime(2099, 1, 1, tzinfo=timezone.utc))
    run(monkeypatch, api, {"D8": q(0.99, 1.0, True, 1.0), "R8": q(0.0, 0.01, True, 0.0)}, st, 1_000, a)
    assert api.orders == []


def test_wide_poly_spread_is_ignored(monkeypatch):
    api = FakeAPI(BOOKS, {})
    st = fresh()
    for t in (1_000, 1_200):
        run(monkeypatch, api, {"D8": q(0.97, 1.0)}, st, t)
    assert api.orders == [] and st["bought"] == {}
