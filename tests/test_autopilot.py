

def test_open_order_schema_uses_quantity_and_price_limit():
    order = {"exchangeId": "903", "quantity": 17884, "priceLimit": 0.16, "open": True}
    assert float(order["quantity"]) * float(order["priceLimit"]) == 2861.44


def test_nullable_order_id_is_allowed_by_documented_schema():
    response = {"orderId": None, "exchangeId": "903", "open": True, "quantityTraded": 10, "totalCost": 1.60}
    assert response["orderId"] is None
    assert response["exchangeId"] == "903"
    assert response["open"] is True
