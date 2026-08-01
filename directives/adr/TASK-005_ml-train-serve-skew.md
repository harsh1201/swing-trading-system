# TASK-005 ML Train/Serve Skew & Training-Data Capture ADR
**Date:** 2026-08-02

## Problem Statement
An audit of the live XGBoost path — verified against the Fly.io logs from the
2026-07-31T20:56Z run — found the ML layer running end to end but predicting on a
corrupted input, with no way to measure or improve itself.

- **P0-1 — `market_breadth` served as `0.0` on every live path.** All three
  screener scoring sites (`run_screener`, `run_screener_short`, and
  `_recompute_ml_for_trade`) passed a hardcoded `0.0` as the breadth feature,
  while `backtest.py` — which generates the training CSVs — passed the real value
  from `calculate_market_breadth`. Training rows span roughly 8–96 (mean ≈ 59)
  with **zero** rows at 0.0, so the model was served a value it had never seen,
  on the feature ranked 3rd by gain. Replaying 400 real training rows through the
  saved classifier with breadth swapped to 0.0 moves the win probability by 0.056
  on average (max 0.214) and flips **37% of long rows across the live 0.45 gate**.
  Every ML Win Prob posted to Discord since launch was computed this way.
- **P0-2 — Regression training crashed; one model never existed.**
  `train_model(mode="regression")` called
  `compute_class_weight("balanced", classes=[0,1], y=r_multiple)`, which raises
  `ValueError` on continuous targets. `models/xgb_target_short.json` had therefore
  never been produced; the long regressor on disk predates the broken code path.
- **P1-3 — Reported metrics were not out-of-sample.** The 80/20 split used the
  same slice for `eval_set` (early stopping) and for the printed metrics, so the
  numbers flattered a model that had already tuned its stopping point on them.
  Measured honestly, the long classifier scores 0.849 AUC in-sample and **0.494
  on a chronological holdout** — a coin flip. Short: 0.889 / 0.598.
- **P1-4 — The split assumed a chronologically ordered CSV** without enforcing
  it, so a reordered export would leak future trades into the training slice.
- **P1-5 — Feature names discarded at fit time.** Fitting on `df[FEATURES].values`
  dropped column names, so `--importance` printed `f0..f9` and inference passed a
  named DataFrame to an unnamed booster.
- **P2-6 — No live outcome corpus.** `PortfolioTrade` stored `ml_prob`/`ml_r` but
  none of the 10 raw features, and `cleanup_portfolio` deleted CLOSED trades after
  `CLOSED_CLEANUP_DAYS` (15). Six weeks of live signals produced zero reusable
  training rows; training data was still the 2026-06-25 backtest export.

## Decision Made
1. **P0-1:** `load_universe()` fetches and indexes the whole `STOCKS` universe once
   per process (memoised); `market_breadth()` derives the real feature from it via
   the existing `calculate_market_breadth`. Both scan loops now iterate that
   universe instead of re-fetching per ticker, and all three call sites pass the
   measured value. Net fetch count is unchanged.
   - Frames are trimmed to `UNIVERSE_BARS = 300` after indicators are computed.
     The deepest lookback is EMA200; untrimmed cached frames (~2000 bars) would
     cost ~243 MB of resident dataframes on a 1 GB Fly VM, versus ~54 MB trimmed.
     Measured breadth is unaffected (52.9% untrimmed vs 52.2% trimmed).
2. **P0-2:** Class weights are confined to the classification branch;
   `sample_weight` is `None` for regression. `xgb_target_short.json` now trains.
3. **P1-3:** `train_model` splits 60/20/20 chronologically. Early stopping consumes
   the **val** slice; reported metrics come from the untouched **test** slice.
4. **P1-4:** `prepare_training_data` sorts by `signal_date` (`dayfirst=True` — the
   CSVs are `DD-MM-YYYY`) before any split.
5. **P1-5:** Models fit on the `FEATURES` DataFrame, preserving real feature names.
6. **P2-6:** `PortfolioTrade` gains a `features` dict, snapshotted at signal time
   and never refreshed on recompute — it has to keep describing the entry decision.
   `cleanup_portfolio` appends each aged-out CLOSED trade to
   `storage/closed_trades.jsonl` (on the Fly volume) before dropping it, and
   `screener.py --export-live-ml` renders that archive as training rows matching
   the backtest CSV layout, so live outcomes concatenate onto backtest rows.

## Retrain Result — the models have no measurable edge

Data regenerated 2026-08-02 (long 631 trades to 2026-07-27; short 478 to 2026-07-30).
With the split fixed, the honest numbers are:

- **Pooled out-of-fold AUC, 5-fold expanding-window walk-forward, with a
  2000-draw permutation test:**

  | strategy | OOF AUC | null 95% band | p | verdict |
  |---|---|---|---|---|
  | long | 0.525 | [0.445, 0.553] | 0.195 | not distinguishable from chance |
  | short | 0.531 | [0.430, 0.571] | 0.201 | not distinguishable from chance |

- **The MFE regression target fares no better.** `r_multiple` in the export is
  `max_favorable / risk` — Maximum Favourable Excursion, not realised R (hence no
  negative values, and `loss` rows showing positive figures). It is a sensible
  target for placing exits, so it was tested separately: mean Spearman **+0.030**
  (long) / **+0.077** (short), mean top-half-vs-bottom-half lift **+0.01R** /
  **+0.10R**. The model does not rank setups.

- **A naive retrain looks like an improvement and is not.** The long classifier
  reported test AUC 0.690 — but early stopping halted at iteration 0, pinning every
  prediction between 0.490 and 0.510. At that spread **100% of test rows clear the
  0.45 gate**: shipping it would have silently disabled the gate while it still
  appeared to work. Trained to completion instead, test AUC falls to 0.397; the
  validation curve peaks at round 0 and declines monotonically.

- **Root cause is non-stationarity plus a redundant feature set.** Long win rate by
  year: 43.4% (2021) → 32.7% (2023) → 18.4% (2025) → 20.0% (2026). And of the 10
  features, `score_total` is a linear combination of `score_risk`/`score_range`/
  `score_trend`, which themselves derive from `coil_range_pct`/`ema50_gap_pct` —
  roughly 6 independent signals, all describing the same consolidation geometry the
  rules already filtered on. The model is asked to re-rank setups using only the
  information that made them setups.

**No retrained model was committed.** The three git-tracked models were restored with
`git checkout -- models/` and remain at their committed state. `xgb_target_short.json`
is new, untracked, and inert (`USE_XGBOOST_TARGET = False`).

## Feature Exploration — ML still fails, but one rule works

Ten context features (as opposed to more consolidation geometry) were computed for
every existing training row directly from `storage/` history at the signal bar —
no backtest re-run needed, since the CSVs carry `ticker` + `signal_date`. Scripts:
`reports/ml/candidate_features.py`, `reports/ml/evaluate.py`.

**ML verdict is unchanged.** Context features beat geometry in 8 of 8 comparisons,
but nothing reaches significance:

| feature set | long clf AUC (p) | short clf AUC (p) |
|---|---|---|
| baseline (10 geometry) | 0.526 (0.165) | 0.526 (0.239) |
| candidates (10 context) | 0.539 (0.082) | 0.536 (0.171) |
| all 20 | 0.513 (0.290) | 0.550 (0.072) |

Combining all 20 *hurts* long (0.513) — 20 features on 600 rows overfits.

**But a univariate screen found a real, stable effect.** `vol_regime`
(ATR% ÷ its own 100-bar median — is this stock calm or turbulent right now) on the
long side: **p = 0.0003**, the only result surviving Bonferroni correction across
all 40 feature×strategy tests.

- Calm tercile **41.4%** win rate vs turbulent tercile **23.7%** (base rate 31.2%).
- Direction holds in **8 of 8 years** — 2020 +36.7pts, 2022 +38.5pts, 2025 +22.7pts,
  never negative.
- As a plain rule with the threshold learned only from prior folds, walk-forward:
  **31.6% → 34.8% win rate (+3.2pts), positive in 5 of 5 folds**, keeping 64% of
  setups.

Second-ranked was `market_breadth` (p = 0.012, 35.9% vs 24.2%) — the very feature
that P0-1 had been serving as `0.0`. The one baseline feature carrying signal was
the one the bug destroyed.

> The pattern across every test in this ADR: the effects here are univariate and
> monotonic, which a threshold rule captures and a boosted-tree model on 600 rows
> cannot learn without overfitting. The lever is a filter, not a bigger model.

**Not implemented.** Adding a `vol_regime` entry filter changes live trade selection
and discards ~36% of setups; net profitability requires a backtest with the filter
applied, which the +3.2pts win-rate figure does not by itself establish (`r_multiple`
is MFE, so true expectancy cannot be computed from these CSVs).

## Explicitly Not Done
- **`PORTFOLIO_MIN_ML` stays at 0.45.** Owner's call, taken with the 0.494 holdout
  AUC on the table. Until a retrained model clears ~0.55 out-of-sample, that gate
  filters setups on a signal with no demonstrated edge. Revisit after the next
  retrain.
- **No hyperparameter tuning.** With 599 long / 432 short samples against a ~500-row
  rule of thumb and a 31% base rate, a holdout AUC in the 0.50–0.55 band indicates
  the feature set, not the hyperparameters. Tuning there fits noise.
- `USE_XGBOOST_TARGET` remains `False`, so the regressors are trained but not
  consulted live. Only the classifier feeds the gate.

## Verification
- `market_breadth()` returns 52.2% against the cached universe — inside the 8–96
  training range, and non-zero for the first time.
- Both scan loops run end to end on cached data and print real breadth.
- Universe memory measured at 54 MB projected across all 2389 symbols.
- `--importance` prints real feature names, not `f0..f9`.
- 162 unit tests pass, including new coverage for chronological ordering,
  regression training on continuous targets, val/test disjointness, closed-trade
  archival, and the live-ML export round trip.
