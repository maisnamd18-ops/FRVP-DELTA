
import numpy as np
import pandas as pd

def frvp_profile(day_df, rows=60, value_area_pct=70.0):
    lo = float(day_df["Low"].min())
    hi = float(day_df["High"].max())
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return np.nan, np.nan, np.nan

    edges = np.linspace(lo, hi, rows + 1)
    vols = np.zeros(rows, dtype=float)

    for _, r in day_df.iterrows():
        low, high = float(r.Low), float(r.High)
        vol = float(r.Volume) if np.isfinite(r.Volume) else 0.0
        if vol <= 0:
            continue
        if high <= low:
            j = max(0, min(rows - 1, np.searchsorted(edges, float(r.Close), side="right") - 1))
            vols[j] += vol
        else:
            overlap = np.maximum(0.0, np.minimum(edges[1:], high) - np.maximum(edges[:-1], low))
            total = overlap.sum()
            if total > 0:
                vols += vol * overlap / total

    if vols.sum() <= 0:
        return np.nan, np.nan, np.nan

    poc_i = int(np.argmax(vols))
    target = vols.sum() * value_area_pct / 100.0
    left = right = poc_i
    cumulative = vols[poc_i]

    while cumulative < target and (left > 0 or right < rows - 1):
        lv = vols[left - 1] if left > 0 else -1
        rv = vols[right + 1] if right < rows - 1 else -1
        if rv >= lv and right < rows - 1:
            right += 1; cumulative += vols[right]
        elif left > 0:
            left -= 1; cumulative += vols[left]
        else:
            break

    centers = (edges[:-1] + edges[1:]) / 2
    return float(centers[poc_i]), float(edges[right + 1]), float(edges[left])

def previous_session_profile(df, rows=60, va_pct=70.0):
    d = df.copy()
    d["Session"] = d.index.date
    sessions = sorted(d["Session"].unique())
    if len(sessions) < 2:
        return None
    prev_day, current_day = sessions[-2], sessions[-1]
    p = d[d["Session"] == prev_day]
    poc, vah, val = frvp_profile(p, rows, va_pct)
    return {"Current Day": str(current_day), "Previous Day": str(prev_day),
            "POC": poc, "VAH": vah, "VAL": val}
