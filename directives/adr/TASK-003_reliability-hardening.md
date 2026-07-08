# TASK-003 Reliability Hardening ADR
**Date:** 2026-07-08

## Problem Statement
A coverage + edge-case audit of the portfolio/gate path surfaced four issues, all
in money-critical code that could degrade **silently** — the worst failure mode for
a system that posts real trade signals:

- **P1 — Silent ML-gate degradation.** `load_model()` returns `None` on a missing
  file; the screener handled that with a literal `if xgb_clf_model is None: pass`.
  With no classifier, `ml_prob` is absent and `passes_quality()` treats it as
  "missing" → the quality gate silently falls back to **score-only** with no log.
- **P2 — Swallowed exceptions.** `_recompute_ml_for_trade()` wrapped its body in a
  bare `except Exception: pass`, hiding any recurring ML recompute failure.
- **P3 — Un-aging ACTIVE positions.** A *triggered* ACTIVE trade is never aged out.
  If its price feed dies (delist/halt) it can never hit SL/target, so it is tracked
  forever, holding a concurrent-trade slot.
- **P4 — Win-rate dilution.** Win-rate was `wins / total_closed`, but `total_closed`
  includes TRAIL/BREAKEVEN exits, so a *profitable* trailing exit dragged the
  reported win-rate down.

Separately, live portfolio state lives only on the Fly volume (`storage/portfolio.json`)
with no version history, so a bad cleanup/prune was irreversible.

## Decision Made
1. **P1 — Make ML failures loud.** When the classifier fails to load (screener long
   & short paths, and the `update_portfolio` recompute loader), print an explicit
   warning that the gate is running on **SCORE ONLY**. No behaviour change beyond
   visibility — the score-only fallback is still the intended "don't hide blind" path.
2. **P2 — Log, don't swallow.** The bare `except` in `_recompute_ml_for_trade()` now
   prints a per-ticker warning and preserves the trade's prior ML values (never a
   partial write).
3. **P3 — Flag, don't drop.** `cleanup_portfolio()` counts triggered ACTIVE trades
   open longer than `MAX_TRIGGERED_ACTIVE_DAYS` (60) into `active_stale_triggered`
   and surfaces the tickers in the run log for human review. The position is **kept**
   — an open trade is never silently removed (consistent with ADR-002).
4. **P4 — Win-rate over decided trades.** Win-rate is now `wins / (wins + losses)` in
   both the Discord portfolio summary and the console summary. TRAIL/BREAKEVEN exits
   no longer dilute the denominator; the closed **count** still shows all states.
5. **Reversible prunes (local).** `save_portfolio()` now writes a rotating,
   timestamped copy of `portfolio.json` into `storage/backups/` on the same Fly
   volume, keeping the newest `PORTFOLIO_BACKUP_KEEP` (20) versions.
   `restore_portfolio_from_backup()` rolls back to any snapshot. Fully local — no
   external service. (An earlier Supabase design was dropped: state is local on Fly.)

## Components / Files Modified
- `config/settings.py`: add `MAX_TRIGGERED_ACTIVE_DAYS`, `PORTFOLIO_BACKUP_KEEP`;
  strip surrounding quotes in the `.env` loader.
- `screener.py`: loud classifier-missing warnings (P1); logged recompute except (P2);
  `active_stale_triggered` flag + run-log warning (P3); decided-trade win-rate (P4);
  `_backup_portfolio_file()` + `restore_portfolio_from_backup()` + `save_portfolio`
  hook (reversible prunes).
- `tests/unit/test_screener.py`, `tests/unit/test_xgboost_ranker.py`: +26 tests
  across gate edge cases, the silent-degradation contract, P3 flag, P4 win-rate, and
  backup/restore round-trip.

## Alternatives Considered
- **Supabase snapshots:** Rejected — portfolio state is local on the Fly volume; a
  local rotating backup on the same volume is simpler, dependency-free, and matches
  where the data actually lives.
- **Auto-closing stale triggered ACTIVE (P3):** Rejected — removing a still-open
  position loses visibility of a held trade (same principle as ADR-002). Flag for
  review instead.
- **Counting profitable TRAIL as a win (P4):** Rejected for v1 — cleaner to define
  win-rate strictly over decided (win/loss) outcomes and report TRAIL in the count.

## Performance and Security Considerations
Warnings and the win-rate change are O(1). The backup is a single `shutil.copy2` plus
a directory listing per save — negligible, and best-effort (never breaks the save). No
new network calls or dependencies. Backups inherit the volume's existing access scope.

## Definition of Done
- A missing ML classifier prints a visible SCORE-ONLY warning (not a silent `pass`).
- ML recompute failures are logged per ticker, never swallowed.
- Triggered ACTIVE trades open > 60d are flagged in the run log, never removed.
- Win-rate excludes TRAIL/BREAKEVEN from its denominator in both summaries.
- Every save writes a rotating local backup; `restore_portfolio_from_backup()` rolls
  back to any retained snapshot.
- Calibration of the ML threshold (validating 0.45 against a reliability curve) is
  **out of scope** here — it needs the training/validation dataset (follow-up).
