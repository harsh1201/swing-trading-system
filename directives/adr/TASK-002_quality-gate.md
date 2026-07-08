# TASK-002 Signal Quality Gate ADR
**Date:** 2026-07-08

## Problem Statement
The Discord portfolio message had grown unmanageable — a single run posted ~99 cards
(79 ACTIVE + 20 PENDING). The pain was decision overload: too many names to act on.
The system already computes two independent conviction signals per setup — a rule-based
`score` (0–100 = Risk 30 + Range 30 + Trend 40) and an XGBoost `ml_prob` (win probability
0–1) — but neither was used to rank or trim the output. Every setup that passed the
multi-stage screener was tracked and displayed.

## Decision Made
Introduce a single **quality gate** applied at three layers, all governed by one rule and
one pair of config knobs:

1. **Rule** (`passes_quality(score, ml_prob)` in `screener.py`):
   - Both signals present → require `score ≥ PORTFOLIO_MIN_SCORE` **AND** `ml_prob ≥ PORTFOLIO_MIN_ML`.
   - Only one present → gate on whichever is available.
   - Neither present → keep (can't judge — don't hide blind).
2. **Config** (`config/settings.py`): `PORTFOLIO_MIN_SCORE = 50`, `PORTFOLIO_MIN_ML = 0.40`.
   Equal trust in both signals; thresholds tunable without code change.
3. **Three application points:**
   - **Entry gate** — `add_to_portfolio()` rejects sub-gate setups so the portfolio stops
     accumulating low-conviction names (single choke point for long + short).
   - **Display gate** — `format_portfolio_for_discord()` (ACTIVE + PENDING) and
     `send_signals_to_discord()` hide sub-gate rows; headers show honest counts
     (`ACTIVE (20 of 79 shown)`) so nothing disappears silently.
   - **Self-healing prune** — `cleanup_portfolio()` drops PENDING rows below the gate on
     each maintenance cycle (live portfolio state lives on the Fly volume, not the repo,
     so a code-driven prune is the only way to clean existing data).

ACTIVE (open) positions are **never pruned** for quality — only aged out when stale. They
are display-filtered but remain in the portfolio file and counted in the header.

## Components / Files Modified
- `config/settings.py`: add `PORTFOLIO_MIN_SCORE`, `PORTFOLIO_MIN_ML`.
- `screener.py`: add `passes_quality()`; apply in `add_to_portfolio()` (entry),
  `format_portfolio_for_discord()` + `send_signals_to_discord()` (display),
  `cleanup_portfolio()` (prune, with `pending_low_quality` stat surfaced in run log).
- `tests/unit/test_screener.py`: gate logic (both/one/neither), display counts,
  entry rejection, and PENDING low-quality prune (ACTIVE kept).

## Alternatives Considered
- **Multiplicative / EV blend ranking** (`score×ml_prob`, or `ml_prob·ml_r` expected value):
  Rejected for v1 in favor of the user's explicit two-gate AND rule — simpler, interpretable,
  and directly expressible. EV ranking remains a candidate for a later ranking pass.
- **Display-only filter (no entry gate):** Rejected as insufficient — the portfolio file
  would keep growing; the display would mask but not solve accumulation.
- **Hard-pruning ACTIVE positions:** Rejected — hiding/removing an open position because its
  score decayed loses visibility of a trade being held. ACTIVE is display-filtered only.

## Performance and Security Considerations
Gate is a pure O(1) comparison per row; negligible cost. No new I/O or network calls. Prune
reuses the existing `cleanup_portfolio` cycle, so no extra portfolio reads/writes.

## Definition of Done
- New sub-gate setups are neither tracked nor posted.
- Portfolio/signal Discord messages show only qualifying rows with honest `shown/total` counts.
- Existing sub-gate PENDING rows are removed on the next maintenance run and logged.
- ACTIVE positions remain tracked and counted regardless of score.
- Thresholds adjustable via `config/settings.py` alone.
