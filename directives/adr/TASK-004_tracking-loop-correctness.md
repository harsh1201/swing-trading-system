# TASK-004 Tracking-Loop Correctness ADR
**Date:** 2026-07-08

## Problem Statement
A deeper audit of the live `update_portfolio()` loop (verified at runtime and against
the live Fly portfolio) found defects in the core trade-tracking path — the part the
whole system exists to do:

- **P0-1 — CLOSED trades dropped every run.** The save filter was
  `if t["status"] != "CLOSED": updated_trades.append(t)`, so any CLOSED trade — even
  one that just closed — was excluded from the save. No win/loss history ever
  persisted; `CLOSED_CLEANUP_DAYS` was effectively dead code. Confirmed by the live
  portfolio showing `CLOSED: 0`, and reproduced with a unit test (a 3-day-old WIN was
  dropped). This also meant the P4 win-rate fix (ADR-003) operated on always-empty data.
- **P0-2 — Only the latest bar checked for exits.** The loop inspected `df.iloc[-1]`
  only. Because the Fly job is scheduled and normally stopped (skips weekends,
  holidays, failed runs), an exit that occurred on an intervening bar was missed —
  and a trade that had already hit its target could later be mis-recorded as a LOSS.
  A silent, outcome-inverting bug.
- **P1-3 — Non-atomic portfolio write.** `open('w')` → `write` could truncate
  `portfolio.json` if the process died mid-write.
- **P1-4 — Fragile NaN sanitisation.** `json_str.replace(": NaN", ": null")` only
  caught dict-scalar NaN; a NaN inside a list stayed a bare `NaN` token → invalid
  JSON on reload → the whole portfolio read as empty (silent total loss).
- **P2-5 — Backup-on-every-save eviction** (regression from ADR-003). `save_portfolio`
  ran during scans once per added setup, so a single run could evict all rotated
  snapshots, defeating "reversible prunes".

## Decision Made
1. **P0-1:** `update_portfolio()` now appends **all** trades (including CLOSED) to the
   saved set. `cleanup_portfolio()` ages CLOSED out after `CLOSED_CLEANUP_DAYS` on
   later runs, as originally intended.
2. **P0-2:** New `_advance_trade(t, df)` walks **every** fetched bar in chronological
   order, honouring the trade's own `date_added` (trigger floor) and
   `entry_trigger_date` (exit floor). It records the *first* exit chronologically and
   stops. SL is checked before target within a bar (conservative on ambiguous bars).
   A same-bar trigger-then-exit is handled. NaN warmup bars are skipped.
3. **P1-3:** `DataCache.save()` writes to a temp file in the same directory then
   `os.replace()`s over the target — an atomic rename; readers see old-or-new, never
   a half-written file.
4. **P1-4:** New `_json_safe()` recursively converts non-finite floats (anywhere,
   including inside lists) to `None` and normalises float subclasses, with
   `allow_nan=False`. Replaces the string hack.
5. **P2-5:** Backups are now **one snapshot per calendar day** (later same-day saves
   overwrite), keeping the newest `PORTFOLIO_BACKUP_KEEP` days — so scan-time saves
   can't evict daily rollback history.

## Components / Files Modified
- `data/cache.py`: atomic write + `_json_safe()`.
- `screener.py`: `_advance_trade()` + `_parse_ddmmyyyy()`; loop uses them and now
  persists CLOSED; day-based `_backup_portfolio_file()`.
- `tests/unit/test_screener.py`, `tests/unit/test_data_cache.py`: +14 tests
  (multi-bar exit detection, pre-trigger-bar guard, short target, same-bar SL/target,
  CLOSED persistence via a stubbed `update_portfolio`, NaN-in-list round-trip, atomic
  no-temp-left, corrupt-file safety, one-per-day backup + rollback).

## Alternatives Considered
- **Recording gap-through fills at the actual bar price (P2-6):** deferred — the
  system tracks signals, not real fills; exact SL/target levels are acceptable for now.
- **Enforcing MAX_CONCURRENT_TRADES / sector caps at tracking time (P2-7):** left as
  a conscious product decision — the tracker intentionally follows every signal.
- **Retry/backoff around the 160 sequential yfinance fetches (P2-8):** noted, not yet
  addressed; `[NO DATA]` currently keeps the trade untouched (safe).

## Performance and Security Considerations
`_advance_trade` scans ≤30 bars per trade — trivial. Atomic write adds one temp file
per save. Daily backups cap disk at `PORTFOLIO_BACKUP_KEEP` files. No new I/O of note,
no network, no new dependencies.

## Definition of Done
- Closed trades persist and age out per `CLOSED_CLEANUP_DAYS` (win/loss history is real).
- Exits are detected on any fetched bar, in order, even across skipped run-days.
- A crash mid-write cannot truncate `portfolio.json`; NaN anywhere serialises safely.
- Portfolio backups retain ~`PORTFOLIO_BACKUP_KEEP` days of daily rollback points.
- Full suite green (156 passed).
