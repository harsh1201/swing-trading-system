"""Compute candidate context features for existing training rows.

The training CSVs carry ticker + signal_date, and storage/ holds full OHLCV
history, so candidate features can be evaluated without re-running the backtest.
Everything is computed on bars <= the signal bar; nothing looks ahead.
"""
import os
import numpy as np
import pandas as pd

STORAGE = "storage"
NIFTY = "_NSEI"

# Context features — deliberately NOT more consolidation geometry, which is what
# the existing 10 already describe.
CANDIDATES = [
    "trend_age",         # bars since price crossed its EMA50 — how mature is this trend
    "vol_regime",        # current ATR% vs its own recent median — calm or turbulent for THIS stock
    "dist_52w_high",     # room left to the 1-year high
    "mom_60d",           # 60-bar return
    "mom_120d",          # 120-bar return
    "rs_60d",            # 60-bar return minus NIFTY's — genuine relative strength
    "vol_trend",         # 20d avg volume / 60d avg volume — is participation building
    "nifty_vol_regime",  # market-wide turbulence, not stock-specific
    "range_compression", # 20d range / 100d range — coil tightness in its own context
    "gap_vol",           # std of overnight gaps, 20d — how gappy this name is
]


def _load(ticker: str) -> pd.DataFrame | None:
    p = os.path.join(STORAGE, f"{ticker}.csv")
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p, index_col=0, parse_dates=True).sort_index()
    return df if len(df) >= 260 else None


def _atr_pct(df: pd.DataFrame, n: int = 14) -> pd.Series:
    hl = df.High - df.Low
    hc = (df.High - df.Close.shift()).abs()
    lc = (df.Low - df.Close.shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(n).mean() / df.Close * 100


def _features_at(df: pd.DataFrame, i: int, nifty: pd.DataFrame) -> dict | None:
    """Feature values as of bar i. Returns None if history is too short."""
    if i < 260:
        return None
    d = df.iloc[: i + 1]                      # inclusive of signal bar, nothing after
    close = float(d.Close.iloc[-1])

    ema50 = d.Close.ewm(span=50, adjust=False).mean()
    above = d.Close > ema50
    # Bars since the most recent flip in the above/below relationship.
    flip = (above != above.shift()).iloc[-250:]
    idx = np.where(flip.values)[0]
    trend_age = float(len(flip) - idx[-1]) if len(idx) else float(len(flip))

    atr = _atr_pct(d)
    atr_now = float(atr.iloc[-1])
    atr_med = float(atr.iloc[-100:].median())
    vol_regime = atr_now / atr_med if atr_med > 0 else 1.0

    hi252 = float(d.High.iloc[-252:].max())
    dist_52w_high = (hi252 - close) / close * 100 if close > 0 else 0.0

    c60 = float(d.Close.iloc[-61]) if len(d) > 61 else close
    c120 = float(d.Close.iloc[-121]) if len(d) > 121 else close
    mom_60d = (close / c60 - 1) * 100 if c60 > 0 else 0.0
    mom_120d = (close / c120 - 1) * 100 if c120 > 0 else 0.0

    # Align NIFTY on the same date so relative strength is measured over the
    # same window, not just the same number of bars.
    ref_date = d.index[-1]
    ns = nifty.loc[:ref_date]
    if len(ns) > 61:
        n_now, n60 = float(ns.Close.iloc[-1]), float(ns.Close.iloc[-61])
        nifty_ret = (n_now / n60 - 1) * 100 if n60 > 0 else 0.0
        n_atr = _atr_pct(ns)
        n_med = float(n_atr.iloc[-100:].median())
        nifty_vol_regime = float(n_atr.iloc[-1]) / n_med if n_med > 0 else 1.0
    else:
        nifty_ret, nifty_vol_regime = 0.0, 1.0
    rs_60d = mom_60d - nifty_ret

    v20 = float(d.Volume.iloc[-20:].mean())
    v60 = float(d.Volume.iloc[-60:].mean())
    vol_trend = v20 / v60 if v60 > 0 else 1.0

    r20 = float(d.High.iloc[-20:].max() - d.Low.iloc[-20:].min())
    r100 = float(d.High.iloc[-100:].max() - d.Low.iloc[-100:].min())
    range_compression = r20 / r100 if r100 > 0 else 1.0

    gaps = (d.Open / d.Close.shift() - 1).iloc[-20:]
    gap_vol = float(gaps.std() * 100)

    return dict(
        trend_age=trend_age, vol_regime=vol_regime, dist_52w_high=dist_52w_high,
        mom_60d=mom_60d, mom_120d=mom_120d, rs_60d=rs_60d, vol_trend=vol_trend,
        nifty_vol_regime=nifty_vol_regime, range_compression=range_compression,
        gap_vol=gap_vol,
    )


def enrich(csv_path: str, out_path: str) -> pd.DataFrame:
    src = pd.read_csv(csv_path)
    src["_dt"] = pd.to_datetime(src.signal_date, dayfirst=True, format="mixed")
    nifty = _load(NIFTY)
    if nifty is None:
        raise SystemExit(f"NIFTY history missing at {STORAGE}/{NIFTY}.csv")

    rows, misses = [], {"no_history": 0, "date_absent": 0, "short_history": 0}
    cache: dict[str, pd.DataFrame] = {}
    for _, r in src.iterrows():
        t = r["ticker"]
        if t not in cache:
            cache[t] = _load(t)
        df = cache[t]
        if df is None:
            misses["no_history"] += 1
            rows.append(None)
            continue
        pos = df.index.searchsorted(r["_dt"])
        # Require an exact bar for that date; a nearest-match would silently use
        # a different day's prices.
        if pos >= len(df) or df.index[pos].date() != r["_dt"].date():
            misses["date_absent"] += 1
            rows.append(None)
            continue
        f = _features_at(df, int(pos), nifty)
        if f is None:
            misses["short_history"] += 1
        rows.append(f)

    feat = pd.DataFrame([r if r else {c: np.nan for c in CANDIDATES} for r in rows])
    out = pd.concat([src.drop(columns="_dt").reset_index(drop=True), feat], axis=1)
    out.to_csv(out_path, index=False)
    kept = out[CANDIDATES].notna().all(axis=1).sum()
    print(f"  {os.path.basename(csv_path)}: {len(src)} rows -> {kept} enriched  {misses}")
    return out


if __name__ == "__main__":
    for s in ("long", "short"):
        enrich(f"reports/ml/training_data_{s}.csv",
               f"reports/ml/training_data_{s}_enriched.csv")
