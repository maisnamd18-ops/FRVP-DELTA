
def detect_poc_signal(df, levels, sl_buffer=0.20, va_pct=70.0):
    if len(df) < 3 or levels is None:
        return None

    # Use the latest completed candle, not a forming candle.
    cur = df.iloc[-2]
    prev = df.iloc[-3]

    poc, vah, val = float(levels["POC"]), float(levels["VAH"]), float(levels["VAL"])
    o, h, l, c = map(float, [cur.Open, cur.High, cur.Low, cur.Close])
    prev_close = float(prev.Close)

    # POC Bounce — original logic preserved.
    if l <= poc <= h:
        if c > poc and c > o:
            entry = c
            sl = l - sl_buffer
            tp = vah
            if entry > sl and tp > entry:
                return {"setup":"POC Bounce","side":"buy","entry":entry,"sl":sl,"tp":tp,
                        "rr":(tp-entry)/(entry-sl)}
        if c < poc and c < o:
            entry = c
            sl = h + sl_buffer
            tp = val
            if sl > entry and tp < entry:
                return {"setup":"POC Bounce","side":"sell","entry":entry,"sl":sl,"tp":tp,
                        "rr":(entry-tp)/(sl-entry)}

    # POC Reversal — original crossing logic, but target adjusted to 2R.
    if prev_close < poc and c > poc and c > o:
        entry, sl = c, l - sl_buffer
        risk = entry - sl
        if risk > 0:
            return {"setup":"POC Reversal","side":"buy","entry":entry,"sl":sl,
                    "tp":entry + 2*risk, "rr":2.0}

    if prev_close > poc and c < poc and c < o:
        entry, sl = c, h + sl_buffer
        risk = sl - entry
        if risk > 0:
            return {"setup":"POC Reversal","side":"sell","entry":entry,"sl":sl,
                    "tp":entry - 2*risk, "rr":2.0}
    return None
