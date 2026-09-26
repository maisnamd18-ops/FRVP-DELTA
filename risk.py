
def position_size(balance, risk_pct, risk_price, product):
    if risk_price <= 0:
        return 0
    risk_money = balance * risk_pct / 100.0
    contract_value = float(product.get("contract_value", 1) or 1)
    raw = risk_money / (risk_price * contract_value)
    step = float(product.get("contract_unit_step", 1) or 1)
    minimum = float(product.get("minimum_order_size", step) or step)
    qty = max(minimum, (raw // step) * step)
    return round(qty, 8)
