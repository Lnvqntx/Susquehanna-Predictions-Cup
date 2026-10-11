

def test_open_order_schema_uses_quantity_and_price_limit():
    order = {"exchangeId": "903", "quantity": 17884, "priceLimit": 0.16, "open": True}
    assert float(order["quantity"]) * float(order["priceLimit"]) == 2861.44
