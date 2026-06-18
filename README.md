# AR Reconciliation & Close Engine

[![CI](https://github.com/ai-frankie/ar-close-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/ai-frankie/ar-close-engine/actions/workflows/ci.yml)

An automated accounts-receivable month-end close, written from the controls up: it computes the subledger, reconciles it to the GL control account, calculates the bad-debt reserve, and runs a SOX-style controls pass — then an **independent reviewer** re-derives the truth from raw data and catches a preparer's errors. Built by an accountant, in code.

> **Thesis:** financial close fails silently — a number is off, nobody knows until audit. This engine makes every figure traceable: subledger → GL → reserve → NRV, each tied and control-checked, with breaks *surfaced* rather than smoothed over.

All data is **synthetic** (fictional customers). No real financial data.

---

## What it does

| Script | Role | Output |
|---|---|---|
| `ar_close.py` | Automated month-end close — subledger, reserve, NRV, GL reconciliation, controls | `AR_Health_Report.xlsx` |
| `ar_issues.py` | Issue scanner — surfaces every exception needing human attention before close | `AR_Issues_Report.xlsx` |
| `ar_review.py` | **Independent QA reviewer** — re-computes truth from raw data, audits a *prepared* workbook | `AR_Close_Review.xlsx` |
| `regen_gl.py` | Regenerates the GL so subledger→GL breaks are discoverable (test-data tooling) | `GL.csv` |

## Verified output (ties to the cent)

`ar_close.py` against the included synthetic data:

```
Subledger 26,713,341.80 | Reserve 1,613,173.40 | NRV 25,100,168.40
Recon: GL 26,711,691.80 - Sub 26,713,341.80 = variance -1,650.00
  auto-identified 3 break(s) net -1,650.00; residual 0.00 -> TIES

CONTROL CHECKS:
  [PASS] GL balanced (debits = credits)        31,594,391.22 = 31,594,391.22
  [PASS] Aging buckets sum to subledger        26,713,341.80
  [PASS] Subledger ties to GL (breaks explain variance)   residual 0.00
  [PASS] Reserve base excludes disputed/un-ageable
  [PASS] NRV positive                          25,100,168.40
ALL CONTROLS PASS
```

## The reviewer is supposed to find errors

`ar_review.py` audits `AR_Close_Prepared_SAMPLE.xlsx` — a *preparer's* workbook with **two planted mistakes**: a double-counted subledger total and a sign-flipped true-up. The reviewer re-derives the correct figures from raw `GL.csv` / `AR_Aging.csv` and flags every figure that doesn't tie:

```
[FAIL] subledger total: reported 53,426,683.60 / expected 26,713,341.80  -> ~2x double-counted (SUM hit a total row)
[FAIL] variance:        reported -26,714,991.80 / expected -1,650.00     -> follows from the doubled subledger
[FAIL] true-up:         reported 1,631,173.40 / expected 1,595,173.40    -> sign flip on opening allowance
```

Two planted errors, **three** flags — the variance fails too, because it's derived from the doubled subledger. That's the point: an independent recomputation surfaces the original error *and* everything downstream of it, before any of it reaches the GL. Segregation of duties, in code.

## Accounting methodology

`ar-reconciliation.md` is the full reference the engine implements: every journal entry in the AR lifecycle (sale → reserve → write-off → recovery), reserve/NRV methodology, SOX controls, Excel aging formulas, and subledger-to-GL reconciliation.

## Scope & limitations

Built to demonstrate the *controls logic* of an AR close, not as a hardened production system. Honest boundaries:

- **Scales linearly, not a volume constraint.** All passes are O(n). On a stress run of 50,000 invoices + 100,000 GL lines (100× the included demo) it closes in **under a second** — volume isn't where this would break.
- **Money is float, rounded to the cent** — not `decimal.Decimal`. Exact at any realistic AR size here; for a production ledger I'd move money to `Decimal` with explicit rounding.
- **Fixed column schema.** It expects specific headers (`Open_Balance`, `Due_Date`, `Account_Number`, …). Real ERP exports vary — a production version needs a column-mapping layer and handling for multi-currency, partial payments, and credit-memo formats.
- **In-memory.** Loads the whole CSV; fine to hundreds of thousands of rows, not a streaming/DB design for millions.
- **Synthetic data only**, fictional customers. Business parameters (as-of date, opening allowance, loss rates) are constants, not config.

The reconciliation control is real, not cosmetic: on the stress run with a deliberately mismatched GL, it correctly **fails to tie** rather than smoothing the gap over.

## Run it

Requires Python 3.11+ and `openpyxl`.

```bash
pip install -r requirements.txt
python ar_close.py     # automated close + controls
python ar_issues.py    # exception scanner
python ar_review.py    # independent reviewer (catches planted errors)
```

No config, no network, no keys — runs on the included synthetic data out of the box.

## Tests

```bash
pip install -r requirements.txt pytest
pytest -v
```

`test_ar_close.py` — **25 tests**, run in CI on every push. They assert the close ties to the cent (subledger `26,713,341.80`, reserve `1,613,173.40`, NRV `25,100,168.40`, recon residual `0.00`, all five controls pass) and that the independent reviewer catches **both** planted preparer errors (the double-counted subledger and the sign-flipped true-up). The scripts expose `run_close()` / `compute_truth()` / `run_review()` so the logic is testable without side effects — `import ar_close` does nothing until you call it.
