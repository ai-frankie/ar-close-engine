---
name: ar-reconciliation
description: Execute the full AR accounting cycle — journal entries, reserve calculation, write-offs, recoveries, SOX controls, Excel aging formulas, subledger-to-GL reconciliation, and management reporting.
category: Accounting
risk: low
date_added: 2026-05-27
triggers:
  - AR aging
  - allowance for doubtful accounts
  - bad debt
  - bad debt expense
  - reserve calculation
  - write-off
  - credit memo
  - AR reconciliation
  - month-end close
  - collections
  - subledger
  - net realizable value
  - accounts receivable reconciliation
  - aging report
  - doubtful accounts
---

# AR Reconciliation & Accounting Cycle

Full reference for the AR accounting cycle. Covers every journal entry, reserve methodology, SOX controls, Excel formulas, and management reporting. Drop any section directly into reports, close packages, or audit prep.

---

## 1. FULL AR LIFECYCLE — Journal Entries

### Step 1 — Original Sale
```
DR  Accounts Receivable          $X
  CR  Revenue                           $X
Memo: Record sale on account. Invoice date = AR entry date.
```

### Step 2 — Month-End Reserve (Bad Debt Expense)
```
DR  Bad Debt Expense             $X
  CR  Allowance for Doubtful Accounts   $X
Memo: Estimate of uncollectible AR. Matches expense to revenue period (matching principle).
      Reserve is an ESTIMATE — requires management judgment, not a write-off decision.
```

### Step 3 — Write-Off (customer confirmed uncollectible)
```
DR  Allowance for Doubtful Accounts    $X
  CR  Accounts Receivable                     $X
Memo: Remove specific customer from AR. Requires manager/controller approval.
      Issue credit memo in subledger to clear customer from aging report.
      Write-off does NOT hit P&L — reserve was already expensed in Step 2.
```

### Step 4 — Recovery (customer pays after write-off)

**Step 4a — Reinstate the AR:**
```
DR  Accounts Receivable          $X
  CR  Allowance for Doubtful Accounts   $X
Memo: Reverse the write-off. Requires same approval level as original write-off.
```

**Step 4b — Apply cash payment:**
```
DR  Cash                         $X
  CR  Accounts Receivable               $X
Memo: Record actual payment. Now aging is clean.
```

### Step 5 — Reserve Release (allowance overfunded)
```
DR  Allowance for Doubtful Accounts    $X
  CR  Bad Debt Expense                        $X
Memo: ONLY time Bad Debt Expense is CREDITED (reduces expense = income effect).
      Use when actual write-offs come in lower than reserved.
      Requires controller approval — direct P&L impact.
```

---

## 2. RESERVE CALCULATION METHOD

### Aging Bucket Approach (Standard)

| Aging Bucket | AR Balance | Historical Loss Rate | Required Reserve |
|---|---|---|---|
| Current (0–30) | $500,000 | 0.5% | $2,500 |
| 31–60 days | $150,000 | 2.0% | $3,000 |
| 61–90 days | $75,000 | 5.0% | $3,750 |
| 91–120 days | $40,000 | 15.0% | $6,000 |
| 120+ days | $20,000 | 40.0% | $8,000 |
| **Total** | **$785,000** | | **$23,250** |

**Required Allowance for Doubtful Accounts balance = $23,250**

> **Adjustment entry:** Compare required balance to current balance on books.
> - If current < required → DR Bad Debt Expense / CR Allowance (Step 2)
> - If current > required → DR Allowance / CR Bad Debt Expense (Step 5)

### Alternative Estimation Methods (per AccountingTools)
- **Historical percentage** — flat % of total AR based on past experience. Best for large volumes of small balances with stable credit policy.
- **Risk classification** — assign risk score per customer, apply higher loss rate to riskier customers. Better for concentrated portfolios.
- **Pareto analysis** — individually review top accounts (the 20% that make up 80% of AR balance). Apply historical % to the remaining tail. Best for mixed portfolios with a few large customers.

### Key Principles
- **Matching principle** — Bad Debt Expense hits the same period as the revenue it relates to.
- **Reserve is an estimate** — based on aging + historical loss rates.
- **Write-off is a management decision** — requires approval, happens after collection efforts exhausted.
- **Gap between reserve and write-off is intentional** — still pursuing collection during that gap.

---

## 3. KEY CONCEPTS

| Term | Where It Lives | What It Means |
|---|---|---|
| Bad Debt Expense | P&L (Income Statement) | The period's estimated uncollectible amount |
| Allowance for Doubtful Accounts | Balance Sheet (contra asset) | Cumulative reserve offsetting gross AR |
| Net Realizable Value | Balance Sheet | Gross AR minus Allowance — what you expect to collect |
| Accounts Receivable (gross) | Balance Sheet | Total outstanding invoices |
| Credit Memo | AR Subledger | Document that removes a specific invoice/customer from aging |

**Balance Sheet presentation:**
```
Accounts Receivable (gross)           $785,000
Less: Allowance for Doubtful Accounts  (23,250)
Net Accounts Receivable               $761,750  ← Net Realizable Value
```

**Contra asset:** Allowance is paired with and offsets AR. It is NOT a liability.

### Critical Auditor Questions

| Auditor asks | Your answer |
|---|---|
| "Why is this customer still on aging if you already reserved it?" | Reserve = estimate of loss. Still actively collecting. Write-off requires approval and only happens after collection exhausted. |
| "What's the difference between Bad Debt Expense and Allowance?" | Expense = P&L, hits when reserved. Allowance = balance sheet reserve account. Two different accounts, same event. |
| "Why did you credit Bad Debt Expense?" | Reserve release — allowance was overfunded vs. required balance. Controller-approved. |
| "When was this timing-sensitive report generated?" | Aging reports generated mid-month can understate receivables — month-end billing not yet posted. |

---

## 4. SOX COMPLIANCE CHECKLIST

### Write-Off Controls
- [ ] Manager or controller approval documented (email, system approval, signed memo)
- [ ] Credit memo issued in subledger — clears customer from aging
- [ ] Credit memo includes: invoice #, customer name, amount, approval date
- [ ] Supporting documentation retained (collection history, final demand letter)

### Reinstatement Controls
- [ ] Same approval level required as original write-off
- [ ] Documentation of why customer paid (and why reversal is appropriate)

### Reserve Release Controls
- [ ] Controller approval required (direct P&L impact)
- [ ] Reserve calculation worksheet shows required vs. book balance
- [ ] Variance explanation documented

### Segregation of Duties
- [ ] Person applying cash receipts ≠ person who approved write-off
- [ ] Person creating credit memos ≠ person approving them
- [ ] Reserve calculation preparer ≠ controller who approves it

### Audit Trail Requirements
- [ ] All journal entries have supporting documentation attached
- [ ] JE preparer and approver are different individuals
- [ ] No manual JEs posted directly to GL AR account without subledger tie-out
- [ ] Reserve calculation retained for each month-end close

---

## 5. EXCEL FORMULAS FOR AR AGING

### Aging Bucket Label (dynamic — recalculates daily)
```excel
=IF(TODAY()-E2<=30,"Current",IF(TODAY()-E2<=60,"31-60",IF(TODAY()-E2<=90,"61-90","90+")))
```
`E2` = Due Date. Use in a "Bucket" column alongside each invoice row.

### Days Past Due (number)
```excel
=TODAY()-E2
```
Returns positive number = days overdue. Negative = not yet due.

### Payment Terms at Origination (static — based on original invoice dates)
```excel
=IF(C2-B2<=30,"Net 30",IF(C2-B2<=60,"Net 60","Net 90+"))
```
`B2` = Invoice Date, `C2` = Due Date. Shows original terms — does NOT change daily.

### Multi-Column Aging (balance appears in correct bucket column, blank in others)
```excel
F2 (0–30 days):   =IF(TODAY()-E2<=30,H2,"")
G2 (31–60 days):  =IF(AND(TODAY()-E2>30,TODAY()-E2<=60),H2,"")
H2 (61–90 days):  =IF(AND(TODAY()-E2>60,TODAY()-E2<=90),H2,"")
I2  (90+ days):   =IF(TODAY()-E2>90,H2,"")
```
`H2` = Balance Due. Use column totals to get bucket subtotals for the reserve table.

> ⚠️ Note: The I2 formula above returns the balance value (not "90+" text) so SUMIFS can total it. Adjust if you want text labels in that column instead.

### SUMPRODUCT — Total AR per Customer in a Specific Bucket
```excel
=SUMPRODUCT((B2:B151=A2)*(H2:H151>0)*(TODAY()-E2:E151<=30)*(H2:H151))
```
Returns total current-bucket balance for the customer in A2. Use bounded ranges (not full columns) to avoid performance issues.

### SUMIFS vs SUMPRODUCT — Decision Rule

| Use | When |
|---|---|
| `SUMIFS` | Simple criteria — match a value, check a status flag, standard operators (`=`, `>`, `<`) |
| `SUMPRODUCT` | Date math inside the condition — `TODAY()-DueDate` requires array evaluation that `SUMIFS` can't handle natively |

---

## 6. RECONCILIATION STEPS — Subledger to GL

### Standard Month-End Close Procedure

1. **Run AR aging report** from subledger (ERP/accounting system). Foot the total.
2. **Pull GL AR control account balance** as of same date.
3. **Compare** — they must tie to the penny.
4. **If they don't tie:**
   - Search GL for manual journal entries posted directly to the AR account
   - Look for JEs with no invoice number or customer reference
   - Common cause: someone debited/credited GL AR directly, bypassing subledger
5. **Fix:** Reverse the out-of-balance JE. Repost correctly through subledger (create proper invoice/credit memo).
6. **Document variance** and resolution in close package.

### Tie-Out Format (for close package)
```
AR Subledger Total (aging report footer):    $785,000.00
GL AR Control Account Balance:               $785,000.00
Variance:                                    $       0.00  ✓ Ties
```

---

## 7. WHEN TO USE THIS SKILL

- Building or reviewing AR aging reports in Excel
- Drafting month-end close journal entries for AR reserve
- Preparing reserve calculation worksheet for controller/manager review
- Responding to auditor questions on write-off timing or reserve methodology
- Drafting management reports on AR health
- SOX control documentation for AR processes
- Interview prep for accounting/controller/AR analyst roles
- Onboarding a new AR analyst or accounting staff

---

## 8. MANAGEMENT REPORT TEMPLATE OUTLINE

When drafting AR report to manager/controller, include these sections:

```
AR HEALTH REPORT — [Month] [Year]
Prepared by: [Name]   |   Date: [Date]   |   Approved by: [Controller]

1. TOTAL AR BALANCE
   Current month:    $___________
   Prior month:      $___________
   Change ($):       $___________
   Change (%):       ____%

2. AGING SUMMARY
   Bucket          Balance      % of Total
   Current         $________    ___%
   31–60 days      $________    ___%
   61–90 days      $________    ___%
   91–120 days     $________    ___%
   120+ days       $________    ___%
   TOTAL           $________    100%

3. RESERVE STATUS
   Required reserve (per aging calc):   $__________
   Current allowance balance (GL):      $__________
   Variance:                            $__________
   Proposed adjustment entry:
     DR Bad Debt Expense / CR Allowance  $__________   [if underfunded]
     DR Allowance / CR Bad Debt Expense  $__________   [if overfunded]

4. WRITE-OFFS THIS PERIOD
   Customer        Invoice #    Amount    Approval    Date
   ___________     _______      $______   __________  _____

5. RECOVERIES THIS PERIOD
   Customer        Invoice #    Amount    Date Received
   ___________     _______      $______   _____________

6. TOP 10 PAST DUE ACCOUNTS (by balance)
   Rank  Customer    Bucket    Balance    Collection Status
   1.    ________    ______    $______    ____________________
   ...

7. COLLECTIONS ACTIONS — 90+ BUCKET
   [For each account: last contact date, response, next action, escalation status]

8. NET REALIZABLE VALUE
   Gross AR:                  $__________
   Less: Allowance:           ($__________)
   Net Realizable Value:      $__________
```

---

## QUICK REFERENCE — All Journal Entries

| Transaction | Debit | Credit |
|---|---|---|
| Sale on account | Accounts Receivable | Revenue |
| Month-end reserve | Bad Debt Expense | Allowance for Doubtful Accounts |
| Write-off | Allowance for Doubtful Accounts | Accounts Receivable |
| Recovery — reinstate | Accounts Receivable | Allowance for Doubtful Accounts |
| Recovery — cash | Cash | Accounts Receivable |
| Reserve release | Allowance for Doubtful Accounts | Bad Debt Expense |
