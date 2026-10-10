from models.orderbook import Ask, fill_budget


def test_fill_budget_walks_best_prices_first():
    result = fill_budget(
        [Ask(0.80, 10), Ask(0.82, 10)],
        budget=15.0,
        max_price=0.82,
    )
    assert result.contracts == 18
    assert round(result.cost, 2) == 14.60
    assert result.worst_price == 0.82
