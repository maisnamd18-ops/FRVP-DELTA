
import hashlib, hmac, json, time
import requests
import pandas as pd

BASE = "https://api.india.delta.exchange"

class DeltaClient:
    def __init__(self, api_key="", api_secret=""):
        self.api_key, self.api_secret = api_key, api_secret

    def _sign(self, method, path, query="", body=""):
        ts = str(int(time.time()))
        msg = method + ts + path + query + body
        sig = hmac.new(self.api_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
        return ts, sig

    def _request(self, method, path, params=None, payload=None, auth=False):
        params = params or {}
        body = json.dumps(payload, separators=(",", ":")) if payload else ""
        headers = {"Accept":"application/json", "User-Agent":"frvp-poc-v12", "Content-Type":"application/json"}
        if auth:
            if not self.api_key or not self.api_secret:
                raise RuntimeError("Delta API credentials are missing from Streamlit Secrets.")
            query = ("?" + "&".join(f"{k}={v}" for k,v in params.items())) if params else ""
            ts, sig = self._sign(method, path, query, body)
            headers.update({"api-key":self.api_key, "timestamp":ts, "signature":sig})
        r = requests.request(method, BASE+path, params=params, data=body, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data.get("success", True):
            raise RuntimeError(str(data))
        return data.get("result", data)

    def get_product(self, symbol):
        try:
            return self._request("GET", f"/v2/products/{symbol}")
        except Exception:
            data = self._request("GET", "/v2/products", params={"states":"live","page_size":100})
            for p in data:
                if str(p.get("symbol","")).upper() == symbol.upper():
                    return p
        return None

    def get_candles(self, symbol, timeframe, limit=500):
        # Delta's OHLC endpoint is intentionally wrapped here; the exact resolution
        # mapping can be changed without touching the strategy engine.
        resolution = {"1m":"1m","5m":"5m","15m":"15m","30m":"30m","1h":"1h"}[timeframe]
        data = self._request("GET", "/v2/history/candles",
                             params={"symbol":symbol, "resolution":resolution, "limit":limit})
        rows = data if isinstance(data, list) else data.get("result", data)
        out = pd.DataFrame(rows)
        if out.empty:
            return out
        # Delta responses may use timestamp/open/high/low/close/volume.
        out.columns = [str(c).lower() for c in out.columns]
        rename = {"timestamp":"Timestamp","open":"Open","high":"High","low":"Low","close":"Close","volume":"Volume"}
        out = out.rename(columns=rename)
        if "Timestamp" in out:
            out.index = pd.to_datetime(out["Timestamp"], unit="s", utc=True).tz_convert("Asia/Kolkata")
        return out[["Open","High","Low","Close","Volume"]].astype(float).sort_index()

    def place_bracket_market_order(self, symbol, side, size, stop_price, take_profit_price):
        product = self.get_product(symbol)
        payload = {
            "product_id": product["id"],
            "product_symbol": symbol,
            "size": size,
            "side": side,
            "order_type": "market_order",
            "bracket_stop_loss_price": str(stop_price),
            "bracket_take_profit_price": str(take_profit_price),
        }
        return self._request("POST", "/v2/orders", payload=payload, auth=True)
