from src.rotator import _buy_price, _expected_return, _sell_price, make_rotation_plan, Opportunity, PositionView


def test_sell_price_yes_uses_yes_bid():
    assert _sell_price("YES", {"bestBid": 0.42, "bestAsk": 0.43}) == 0.42


def test_sell_price_no_uses_complement_of_yes_ask():
    assert _sell_price("NO", {"bestBid": 0.42, "bestAsk": 0.43}) == 0.57


def test_buy_price_no_uses_complement_of_yes_bid():
    row = {"buy_yes": 0.43, "buy_no": 0.58}
    assert _buy_price("NO", row) == 0.58


def test_expected_return():
    assert round(_expected_return(0.60, 0.50), 6) == 0.20


def test_rotation_requires_material_improvement():
    position = PositionView(
        exchange_id="old",
        market_id="1",
        title="Old market",
        side="YES",
        quantity=100,
        avg_cost=0.50,
        current_price=0.50,
        market_value=50.0,
        cost_basis=50.0,
        model_probability=0.56,
        executable_exit_price=0.49,
        hold_return=_expected_return(0.56, 0.49),
    )
    opportunity = Opportunity(
        exchange_id="new",
        market_id="2",
        title="New market",
        side="YES",
        model_probability=0.62,
        executable_buy_price=0.50,
        edge=0.12,
        expected_return=_expected_return(0.62, 0.50),
        spread=0.01,
        forecast_asof=None,
    )
    plan = make_rotation_plan([position], [opportunity], min_improvement=0.05)
    assert plan is not None
    assert plan.sell_quantity == 100
    assert plan.buy_quantity > 0
    assert plan.improvement >= 0.05


def test_rotation_returns_none_below_threshold():
    position = PositionView(
        exchange_id="old",
        market_id="1",
        title="Old market",
        side="YES",
        quantity=100,
        avg_cost=0.50,
        current_price=0.50,
        market_value=50.0,
        cost_basis=50.0,
        model_probability=0.53,
        executable_exit_price=0.50,
        hold_return=_expected_return(0.53, 0.50),
    )
    opportunity = Opportunity(
        exchange_id="new",
        market_id="2",
        title="New market",
        side="YES",
        model_probability=0.56,
        executable_buy_price=0.54,
        edge=0.02,
        expected_return=_expected_return(0.56, 0.54),
        spread=0.01,
        forecast_asof=None,
    )
    assert make_rotation_plan([position], [opportunity], min_improvement=0.05) is None


def test_rotation_does_not_choose_an_opportunity_from_an_already_held_market():
    from src.rotator import build_opportunities

    markets = [
        {
            "id": "214",
            "title": "Will the Republican Party win the IA-01 House race?",
            "status": "open",
            "categories": [],
            "exchanges": [{"id": "903", "option": "YES", "initialPrice": 0.50}],
        }
    ]
    quotes = [
        {"exchangeId": "903", "latestPrice": 0.165, "bestBid": 0.160, "bestAsk": 0.165, "spread": 0.005}
    ]
    forecasts = {
        "IA-01": {"asOf": None, "rating": None, "democratic": 0.50, "republican": 0.50}
    }

    opportunities = build_opportunities(
        markets,
        quotes,
        forecasts,
        occupied_exchanges=set(),
        occupied_markets={"214"},
        min_edge=0.01,
        max_spread=0.02,
    )
    assert opportunities == []
