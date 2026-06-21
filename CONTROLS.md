# AR Internal Controls — Controller's Reference

This document describes the SOX-style internal controls the AR close engine performs, written for a **controller reviewing a month-end close package**. Every control states its objective, the risk it mitigates, the financial-statement assertion it supports, and the exact flag it raises.

All data is **synthetic** (fictional customers). The point is the *controls logic*, not the numbers.

---

## How to read this document

- **AUTOMATED** — the engine computes the test and returns **PASS / FAIL**. A FAIL must be resolved before sign-off.
- **EVIDENCED** — the engine produces the **exception population** a human control reviews. It returns **OK** (nothing to review) or **REVIEW** (items for controller judgment). It does not auto-fail, because the judgment is the controller's.
- Financial-statement **assertions**: *completeness* (nothing omitted), *existence/occurrence* (it really happened), *accuracy/valuation* (right amount), *cutoff* (right period), *presentation* (shown correctly).

Run the register with:

```bash
python ar_controls.py
```

## Close package reading order

A controller signs from the bottom up — you cannot trust a reconciliation built on a corrupt ledger. So the engine is ordered:

1. **Data integrity** — is the ledger and subledger feed even clean? (C2, C4, C5)
2. **Reconciliation** — does the subledger tie to the GL, and is every GL posting authorized? (C8, C9, C10)
3. **Completeness & valuation** — are all receivables recorded at NRV, with adequate reserves? (C-R1, allowance adequacy)
4. **AR process** — aging, write-off candidates, disputed invoices
5. **Review & segregation of duties** — independent re-performance (C21, the reviewer)

---

## Section 1 — Data integrity controls

These are the bedrock. Every financial figure sits on top of them.

### C2 — GL posting hygiene · *accuracy/valuation* · AUTOMATED
**Objective:** every GL row is structurally valid before any AR figure derived from the ledger is relied upon — unique non-blank `Entry_ID`, exactly one of Debit/Credit populated, a recognized account.
**Risk:** a malformed ledger line silently corrupts every total built from it.
**Flag:** `C2: {n} malformed GL line(s)` — blank/duplicate Entry_ID, both-or-neither Debit/Credit, unknown account. PASS when n = 0.

### C4 — Unique primary keys · *accuracy/valuation* · AUTOMATED
**Objective:** the natural key of each subledger and the GL is unique — no duplicate `Invoice_Number` or `Entry_ID`.
**Risk:** a duplicated key double-counts a transaction — the most common cause of an overstated receivable or a double collection.
**Flag:** `DUPLICATE KEY in {table} — {value} appears {n} times`. FAIL on any GL or aging duplicate.

### C5 — Referential integrity · *existence/occurrence* · AUTOMATED
**Objective:** every AR_Aging row has a customer name, and every GL reference to an aging invoice resolves to the aging subledger.
**Risk:** a vendorless invoice breaks customer reporting; an orphan GL reference (AR control account pointing to an invoice that doesn't exist) is a fraud and data-quality red flag.
**Flag:** `MISSING CUSTOMER`, `ORPHAN GL REF`. FAIL on any orphan GL reference or customerless invoice.

---

## Section 2 — Reconciliation controls

### C8 — Manual / top-side JE to the AR control account · *existence/occurrence* · AUTOMATED
> **This is the control most worth reading.** See the deep-dive below.

**Objective:** every posting to acct 1200 must originate from an authorized subledger feed (`Source` ∈ {Subledger, Opening}) **and** carry a resolvable invoice reference. Direct manual / top-side journal entries that bypass the subledger are itemized for controller sign-off.
**Risk:** the classic **management-override** red flag. A manual debit straight to the AR control account — no invoice, no customer, no approval trail — is exactly how a receivable is overstated or a fictitious AR is parked. External auditors specifically hunt for these.
**Flag (per entry):**
```
MANUAL JE TO AR CONTROL — Entry JE700381 2026-06-15, net +5,000.00;
Source='Manual JE' not a subledger feed; no Invoice_Ref.
Obtain JE approval before sign-off.
```
PASS only when zero manual entries hit acct 1200.

### C9 — Two-way coverage completeness · *completeness* · EVIDENCED
**Objective:** each open invoice has a matching Subledger-source GL debit, and each Subledger-source GL debit maps back to an open invoice.
**Risk:** offsetting errors that **net to zero** hide under the single-balance tie — an invoice missing from the GL plus an unsupported GL debit of equal size cancel out. The two-way population check surfaces them.
**Flag:** `IN SUBLEDGER, NOT GL` / `IN GL, NOT SUBLEDGER` lists for review.

### C10 — Period / cutoff integrity · *cutoff* · AUTOMATED
**Objective:** every GL entry's posting `Date` falls within its stated `Period` and the close window, and no AR-1200 posting falls outside the period.
**Risk:** back-dated or post-period entries push receivables into the wrong month — a cutoff misstatement.
**Flag:** `PERIOD MISMATCH` (Date vs Period) and `OUT-OF-WINDOW` (AR-1200 dated outside the close). FAIL on any out-of-window AR-1200 entry.

---

## Section 3 — Completeness & valuation

### C-R1 — Allowance adequacy / reserve booked to GL 1210 · *accuracy/valuation* · AUTOMATED
**Objective:** the allowance for doubtful accounts on the GL (acct 1210, credit-normal contra-asset) equals the aging-based required reserve. The engine ties the aging reserve calculation to the GL 1210 balance and fails when the allowance is under-booked.
**Risk:** **net realizable value is the #1 AR audit assertion.** An under-booked allowance overstates AR and overstates net income. This control ensures the month-end true-up is booked before close.
**Flag:**
```
UNDER-RESERVED — aging requires 1,600,000.00, GL allowance 1210 shows 18,000.00;
book true-up of 1,582,000.00 before close.
```

---

## Section 4 — AR process controls *(in `ar_close.py`)*

- **AR subledger ties to GL 1200** — the open aging subledger balance equals GL 1200 net.
- **Aging buckets sum to subledger** — the aged buckets add up; no reconciling differences.
- **Aging flags excluded from reserve** — disputed invoices and negative balances are excluded from the reserve base.
- **NRV is positive** — net realizable value (subledger − allowance) must be > 0. If it flips negative, the data is corrupt or the allowance is inverted.
- **Write-off candidates** — invoices over 120 days old with balance > $5,000 (and not disputed) are listed for controller review.

## Section 5 — Review & segregation of duties

### C21 — Single-source prepare-and-pay (SoD proxy) · *existence/occurrence* · EVIDENCED
**Objective:** no single source both raises and clears an AR receivable.
**Flag:** `SELF-CLEARED` items where one non-subledger source posts both legs to acct 1200.
**Honest limitation:** the only preparer/approver signal in this dataset is the GL `Source` field — it is **not a user ID**. A production control would key on the system user who entered vs. who approved each JE. This ships as EVIDENCED with that limitation stated, not as a hard pass/fail.

### Independent re-performance (`ar_review.py`)
A separate reviewer recomputes the truth from raw data and audits a *prepared* workbook, catching planted preparer errors (doubled subledger, omitted allowance, missed write-off) before they reach the GL. **Segregation of duties, in code.**

---

## The manual-JE-to-control-account control, in depth

Why it gets its own section: in a real close, the subledger feeds the GL automatically — AR invoices debit the control account, cash receipts credit it. Those postings carry an invoice reference and a system `Source`. A **manual journal entry posted directly to the AR control account** breaks that chain: it has no invoice behind it and a `Source` that isn't a subledger feed.

That is precisely the entry an auditor circles, because it is how the control account is adjusted *outside the disciplined subledger process* — to hit a target, hide a variance, or park a fictitious receivable. The engine's test is deliberately strict:

```python
flag every GL row where Account_Number == "1200"
  AND ( Source not in {"Subledger", "Opening"}
        OR Invoice_Ref is blank
        OR Invoice_Ref not found in the AR subledger )
```

The included synthetic data contains three organic reconciling items naturally posted to 1200 with no `Invoice_Ref`:
- `Manual JE`: reclass error, +500 (debit)
- `Cash Receipt`: unapplied cash, −3,400 (credit)
- `Manual JE`: credit-memo accrual error, +1,250 (debit)

These three entries net to −1,650, which exactly equals the AR↔GL variance the engine reconciles. The control demonstrably fires on all three. They are not seeded; they are organic to the month-end recon and represent real-world reconciling items a controller would investigate and approve before sign-off.

---

## Assertion coverage map

| Assertion | Controls |
|---|---|
| Completeness | C9 (two-way), C-R1 (reserve), AR aging foots |
| Existence / occurrence | C5 (referential), **C8 (manual JE)**, C21 (SoD) |
| Accuracy / valuation | C2 (hygiene), C4 (keys), **C-R1 (NRV)**, negative-balance check |
| Cutoff | C10 (period) |
| Presentation | aging aging buckets |

## Known limitations & data-coverage gaps

This is a controls **demonstration on synthetic data**, not a production GRC system. It cannot perform controls that require fields this dataset does not carry:

- **No user IDs** — segregation of duties uses the `Source` field as a proxy (C21), not the actual preparer/approver. EVIDENCED only.
- **No customer master** — name-variant and one-time-customer detection would be heuristic; not implemented as a hard control.
- **No bank-detail change log** — collection-redirection fraud (a key real-world AR control) is out of scope.
- **Money is float, rounded to the cent** — not `decimal.Decimal`.

These gaps are stated plainly because an honest controls inventory names what it does *not* cover.
