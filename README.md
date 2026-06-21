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
| `ar_controls.py` | **Internal controls register** — SOX-style controls: GL hygiene, data integrity, manual-JE detection, cutoff, allowance adequacy, segregation of duties | Console register |
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

## Internal controls register

`ar_controls.py` runs **eight SOX-style controls** on the close, from controller POV:

```
[PASS] C2 GL posting hygiene — unique Entry_IDs, exactly one of Debit/Credit
[PASS] C4 Unique primary keys — no duplicate invoices or GL entries
[PASS] C5 Referential integrity — every GL ref resolves to an invoice
[FAIL] C8 Manual / top-side JE to AR control — 3 manual JEs to 1200 netting -1,650
[OK]   C9 Two-way coverage (subledger ↔ GL) — open invoices covered
[PASS] C10 Period / cutoff integrity — all AR-1200 postings in-period
[FAIL] C-R1 Allowance adequacy (NRV check) — aging requires 1.6M, GL shows 18K
[OK]   C21 Segregation of duties (proxy) — no single-source self-cleared items

SUMMARY: 2 FAIL (C8 manual JEs, C-R1 under-reserved), rest PASS/OK
```

The three manual JEs to 1200 are **organic reconciling items** in the synthetic data (reclass error, unapplied cash, credit-memo accrual error) that net to exactly the AR↔GL variance the close reconciles — the control demonstrably fires and a controller would review & approve them before sign-off. C-R1 fails because the opening allowance (18K) is way below the aging-computed requirement (1.6M), showing the true-up needed.

Full methodology and audit-assertion mapping: see **[CONTROLS.md](CONTROLS.md)**.

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
python ar_controls.py  # SOX-style controls register
python ar_issues.py    # exception scanner
python ar_review.py    # independent reviewer (catches planted errors)
```

No config, no network, no keys — runs on the included synthetic data out of the box.

## Tests

```bash
pip install -r requirements.txt pytest
pytest -v
```

`test_ar_close.py` — **33 tests** (25 core + 8 controls), run in CI on every push. Core tests assert the close ties to the cent (subledger `26,713,341.80`, reserve `1,613,173.40`, NRV `25,100,168.40`, recon residual `0.00`, all five controls pass) and that the independent reviewer catches **both** planted preparer errors (the double-counted subledger and the sign-flipped true-up). Controls tests verify the register has 8 controls, C8 detects the 3 manual JEs, C-R1 detects under-reserving, and PASS/OK/REVIEW verdicts are correct. The scripts expose `run_close()` / `compute_truth()` / `run_review()` / `run_controls()` so the logic is testable without side effects — `import ar_close` does nothing until you call it.
