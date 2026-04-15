# Coverage Report — TASK-QA-001
**Date:** 2026-04-06
**Total Coverage:** 74%

## File Breakdown

| File | Statements | Executed | Coverage | Status |
| :--- | :--- | :--- | :--- | :--- |
| `backtest.py` | 723 | 608 | 84% | ❌ FAIL (Req: 90%+) |
| `screener.py` | 594 | 431 | 73% | ❌ FAIL (Req: 90%+) |
| `strategies/long_breakout.py` | 161 | 147 | 91% | ❌ FAIL (Req: 100%) |
| `strategies/short_breakout.py` | 108 | 98 | 91% | ❌ FAIL (Req: 100%) |
| `data/cache.py` | 31 | 24 | 77% | ⚠️ LOW |
| `data/earnings.py` | 33 | 28 | 85% | 🆗 OK |
| `config/settings.py` | 32 | 32 | 100% | ✅ PASS |
| `config/stocks.py` | 3 | 3 | 100% | ✅ PASS |

## Missing Coverage Details

### `backtest.py` (84%)
- **Missing Lines**: 177, 201, 206, 210, 214, 218, 222, 226, 235, 375-376, 384-385, 400-401, 418-424, 436, 441, 444, 460, 465, 469, 475, 487, 496, 502, 531-541, 574, 608-610, 638-641, 807-808, 816-817, 834-842, 863, 867, 870, 873, 877, 881, 885, 895, 1027-1028, 1036-1037, 1048-1049, 1053-1054, 1058, 1077-1081, 1091, 1095, 1098, 1113, 1117, 1121, 1127, 1139, 1146, 1152, 1181-1191, 1294-1304, 1321-1329, 1350-1358.
- **Notes**: Significant gaps in `run_backtest`, `scan_candidates`, and CLI error handling.

### `screener.py` (73%)
- **Missing Lines**: 133, 196, 234-240, 362-387, 473, 485-502, 507-522, 533-580, 619-635, 663-680, 720-726, 836-860, 943-1001, 1003-1050, 1089-1105, 1135-1140.
- **Notes**: Large portions of the screening engine and display logic are uncovered.

### `strategies/long_breakout.py` (91%)
- **Missing Lines**: 135, 144, 167-168, 252, 255, 305, 331, 440, 446, 452, 455, 460, 468.
- **Notes**: Missing coverage for specific regime checks and breadth calculations.

### `strategies/short_breakout.py` (91%)
- **Missing Lines**: 127, 130, 146-152, 165-166.
- **Notes**: Missing coverage for bearish regime edge cases.

## Recommendations
1.  **Unit Tests**: Add unit tests for the missing branches in `strategies/`.
2.  **Integration Tests**: Implement end-to-end tests for `screener.py` to cover the main execution loop.
3.  **Mocking**: Ensure all error conditions in `backtest.py` are exercised via mocks.
