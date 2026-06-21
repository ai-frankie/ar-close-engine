"""
AR CONTROLS REGISTER — SOX-style internal controls over the AR close.

Each control is written from a CONTROLLER's point of view: it states the control
objective, the risk it mitigates, the financial-statement assertion it supports,
and produces a deterministic PASS / FAIL / REVIEW result with plain-English flags
a controller can act on before signing the close.

Delivery types:
  AUTOMATED — the engine computes the flag and asserts PASS/FAIL.
  EVIDENCED — the engine produces the exception population a human control reviews.

See CONTROLS.md for the full control narrative, assertion map, and limitations.
Run: python ar_controls.py
"""
import csv, os, datetime as dt
from collections import Counter, defaultdict
from ar_close import run_close

D = os.path.dirname(os.path.abspath(__file__))
AR_CONTROL_ACCT = "1200"
ALLOWANCE_ACCT = "1210"
CLOSE_PERIOD = "2026-06"
PERIOD_START = dt.date(2026, 6, 1)
PERIOD_END = dt.date(2026, 6, 30)
AS_OF = dt.date(2026, 6, 17)

# A posting to the AR control account is legitimate only if it came from an
# authorized subledger feed. Anything else is a manual / top-side entry.
SUBLEDGER_SOURCES = {"Subledger", "Opening"}
KNOWN_ACCOUNTS = {"1000", "1100", "1200", "1210", "2000", "3000", "4000",
                  "5000", "6000", "6100", "6300"}


def fnum(x):
    try: return float(str(x).replace(",", ""))
    except (ValueError, TypeError): return None


def fdate(x):
    x = (x or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"):
        try: return dt.datetime.strptime(x, fmt).date()
        except (ValueError, TypeError): pass
    return None


def load(name, data_dir=None):
    p = os.path.join(data_dir or D, name)
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []


def _result(passed, n_exceptions):
    """Map an exception count to a controller verdict."""
    if passed is None:
        return "REVIEW" if n_exceptions else "OK"
    return "PASS" if passed else "FAIL"


# ── individual controls — each returns (control_dict) ────────────────────────

def c2_gl_posting_hygiene(gl):
    """C2 — every GL row is structurally valid before any figure is trusted."""
    exc = []
    seen = Counter(r.get("Entry_ID") for r in gl)
    for r in gl:
        eid = (r.get("Entry_ID") or "").strip()
        dr_raw = (r.get("Debit") or "").strip()
        cr_raw = (r.get("Credit") or "").strip()
        dr, cr = fnum(dr_raw) or 0, fnum(cr_raw) or 0
        if not eid:
            exc.append(f"Blank Entry_ID on a GL line")
        elif seen[eid] > 1:
            exc.append(f"Duplicate Entry_ID {eid} ({seen[eid]} lines)")
        if dr_raw and cr_raw and dr and cr:
            exc.append(f"{eid}: both Debit and Credit populated — malformed line")
        if not dr_raw and not cr_raw:
            exc.append(f"{eid}: neither Debit nor Credit — no amount")
        if str(r.get("Account_Number")).strip() not in KNOWN_ACCOUNTS:
            exc.append(f"{eid}: unrecognized account {r.get('Account_Number')}")
    return {
        "id": "C2", "name": "GL posting hygiene (entry-level data integrity)",
        "objective": "Every GL row is structurally valid — unique Entry_ID, exactly "
                     "one of Debit/Credit populated, recognized account — before any "
                     "AR figure derived from the ledger is relied upon.",
        "assertion": "accuracy/valuation", "delivery": "AUTOMATED",
        "result": _result(len(exc) == 0, len(exc)),
        "detail": f"{len(exc)} malformed GL line(s)",
        "exceptions": exc[:25],
    }


def c4_duplicate_keys(aging, gl):
    """C4 — natural primary keys are unique across subledgers and the GL."""
    exc = []
    for table, rows, key in [
        ("AR_Aging", aging, "Invoice_Number"),
        ("GL", gl, "Entry_ID"),
    ]:
        c = Counter((r.get(key) or "").strip() for r in rows)
        for val, n in c.items():
            if val and n > 1:
                exc.append(f"DUPLICATE KEY in {table} — {key} '{val}' appears {n} times")
    return {
        "id": "C4", "name": "Unique primary keys (Invoice#, Entry_ID)",
        "objective": "The natural key of each subledger and the GL is unique, so no "
                     "transaction is silently counted twice.",
        "assertion": "accuracy/valuation", "delivery": "AUTOMATED",
        "result": _result(len(exc) == 0, len(exc)),
        "detail": f"{len(exc)} duplicate key(s)",
        "exceptions": exc[:25],
    }


def c5_referential_integrity(aging, gl):
    """C5 — every GL reference to an aging invoice resolves."""
    inv_nums = {(r.get("Invoice_Number") or "").strip() for r in aging}
    exc = []
    for a in aging:
        if not (a.get("Customer_Name") or "").strip():
            exc.append(f"MISSING CUSTOMER — invoice {a.get('Invoice_Number')} has no customer name")
    for r in gl:
        if str(r.get("Account_Number")).strip() == AR_CONTROL_ACCT:
            ref = (r.get("Invoice_Ref") or "").strip()
            # Skip opening-balance entries (they don't tie to individual invoices)
            if ref and ref not in inv_nums and ref != "OPENING-AR":
                exc.append(f"ORPHAN GL REF — GL 1200 entry {r.get('Entry_ID')} cites "
                          f"invoice {ref} not in the aging")
    return {
        "id": "C5", "name": "Referential integrity (GL->aging invoice)",
        "objective": "Every AR_Aging row has a customer, and every GL reference to "
                     "an aging invoice resolves — so the control account ties to "
                     "valid, complete receivables.",
        "assertion": "existence/occurrence", "delivery": "AUTOMATED",
        "result": _result(len(exc) == 0, len(exc)),
        "detail": f"{len(exc)} referential break(s)",
        "exceptions": exc[:25],
    }


def c8_manual_je_to_ar_control(gl, aging):
    """C8 — manual / top-side JEs to the AR control account that bypass the
    subledger. THE classic management-override / audit red flag."""
    inv_nums = {(r.get("Invoice_Number") or "").strip() for r in aging}
    flagged = []
    net = 0.0
    for r in gl:
        if str(r.get("Account_Number")).strip() != AR_CONTROL_ACCT:
            continue
        src = (r.get("Source") or "").strip()
        ref = (r.get("Invoice_Ref") or "").strip()
        # Opening entries (cumulative balances) pass; Subledger entries require valid refs
        if src == "Opening":
            continue
        bad_source = src not in SUBLEDGER_SOURCES
        bad_ref = (not ref) or (ref not in inv_nums)
        if bad_source or bad_ref:
            # AR is debit-normal, so net = Debit - Credit
            amt = (fnum(r.get("Debit")) or 0) - (fnum(r.get("Credit")) or 0)
            net += amt
            reason = []
            if bad_source: reason.append(f"Source='{src or 'NONE'}' not a subledger feed")
            if not ref: reason.append("no Invoice_Ref")
            elif ref not in inv_nums: reason.append(f"Invoice_Ref '{ref}' not in subledger")
            flagged.append(f"MANUAL JE TO AR CONTROL — Entry {r.get('Entry_ID')} "
                          f"{r.get('Date')}, net {amt:+,.2f}; {'; '.join(reason)}. "
                          f"Obtain JE approval before sign-off.")
    return {
        "id": "C8", "name": "Manual / top-side JE to AR control account (subledger bypass)",
        "objective": "Every posting to acct 1200 must originate from an authorized "
                     "subledger feed (Subledger, Opening) and carry a resolvable "
                     "invoice reference. Direct manual entries that bypass the subledger "
                     "are itemized for controller sign-off — the classic override risk.",
        "assertion": "existence/occurrence", "delivery": "AUTOMATED",
        "result": _result(len(flagged) == 0, len(flagged)),
        "detail": f"{len(flagged)} manual JE(s) to acct 1200 netting {net:+,.2f}",
        "exceptions": flagged[:25],
    }


def c9_two_way_coverage(aging, gl):
    """C9 — two-way population tie beneath the net-balance reconciliation."""
    open_invs = {(a.get("Invoice_Number") or "").strip()
                 for a in aging
                 if (fnum(a.get("Open_Balance")) or 0) > 0.005}
    gl_refs = {(r.get("Invoice_Ref") or "").strip() for r in gl
               if str(r.get("Account_Number")).strip() == AR_CONTROL_ACCT
               and (r.get("Source") or "").strip() == "Subledger"}
    in_sub_not_gl = open_invs - gl_refs
    in_gl_not_sub = {r for r in gl_refs if r} - open_invs
    exc = ([f"IN SUBLEDGER, NOT GL — open invoice {x} has no Subledger-source GL debit" for x in list(in_sub_not_gl)[:12]]
           + [f"IN GL, NOT SUBLEDGER — GL debit refs invoice {x} not in subledger" for x in list(in_gl_not_sub)[:12]])
    return {
        "id": "C9", "name": "Subledger-to-GL coverage completeness (two-way tie)",
        "objective": "Each open invoice has a matching Subledger-source GL debit and each "
                     "Subledger-source GL debit maps back to an invoice — catching offsetting "
                     "errors that net to zero and hide under the single-balance tie.",
        "assertion": "completeness", "delivery": "EVIDENCED",
        "result": _result(None, len(exc)),
        "detail": f"{len(in_sub_not_gl)} in-subledger-not-GL, {len(in_gl_not_sub)} in-GL-not-subledger",
        "exceptions": exc,
    }


def c10_cutoff_integrity(gl):
    """C10 — postings land in the correct period; no AR-1200 posting outside the window."""
    exc = []
    for r in gl:
        d = fdate(r.get("Date"))
        period = (r.get("Period") or "").strip()
        if d and period and d.strftime("%Y-%m") != period:
            exc.append(f"PERIOD MISMATCH — Entry {r.get('Entry_ID')} dated {r.get('Date')} "
                      f"tagged period {period}")
        if str(r.get("Account_Number")).strip() == AR_CONTROL_ACCT and d:
            if d < PERIOD_START or d > PERIOD_END:
                exc.append(f"OUT-OF-WINDOW — AR-1200 entry {r.get('Entry_ID')} dated "
                          f"{r.get('Date')} outside close {CLOSE_PERIOD}")
    return {
        "id": "C10", "name": "Period / cutoff integrity of GL & AR postings",
        "objective": "Every GL entry's posting date falls within its stated period and "
                     "the close window, so receivables and collections land in the "
                     "correct month.",
        "assertion": "cutoff", "delivery": "AUTOMATED",
        "result": _result(len(exc) == 0, len(exc)),
        "detail": f"{len(exc)} cutoff exception(s)",
        "exceptions": exc[:25],
    }


def c_r1_allowance_adequacy(gl, data_dir=None):
    """C-R1 — the allowance for doubtful accounts on the GL (acct 1210) must
    equal the aging-based required reserve; the gap is the true-up needed."""
    # Compute required reserve using ar_close
    close_result = run_close(data_dir)
    required = close_result["reserve"]

    # Compute GL allowance: 1210 is credit-normal contra-asset, so net = Credit - Debit
    gl_allowance = round(sum((fnum(r.get("Credit")) or 0) - (fnum(r.get("Debit")) or 0)
                             for r in gl if str(r.get("Account_Number")).strip() == ALLOWANCE_ACCT), 2)

    booked = abs(required - gl_allowance) < 0.01
    gap = required - gl_allowance
    exc = [] if booked else [
        f"UNDER-RESERVED — aging requires {required:,.2f}, GL allowance 1210 shows "
        f"{gl_allowance:,.2f}; book true-up of {gap:,.2f} before close."
    ]
    return {
        "id": "C-R1", "name": "Allowance adequacy / reserve booked to GL 1210",
        "objective": "The allowance for doubtful accounts on the GL (acct 1210) must "
                     "equal the aging-based required reserve; the gap is the true-up "
                     "that must be posted before close. Under-reserving overstates AR NRV.",
        "assertion": "accuracy/valuation", "delivery": "AUTOMATED",
        "result": _result(booked, 0 if booked else 1),
        "detail": f"computed {required:,.2f} vs GL 1210 {gl_allowance:,.2f}"
                  + ("" if booked else " — UNDER-RESERVED"),
        "exceptions": exc,
    }


def c21_segregation_of_duties(gl):
    """C21 — single-source prepare-and-pay on the AR control account (EVIDENCED).
    Source is the only preparer/approver proxy in this dataset — see limitations."""
    by_ref = defaultdict(list)
    for r in gl:
        if str(r.get("Account_Number")).strip() == AR_CONTROL_ACCT:
            by_ref[(r.get("Invoice_Ref") or "").strip()].append(r)
    exc = []
    for ref, legs in by_ref.items():
        if not ref:
            continue
        sources = {(l.get("Source") or "").strip() for l in legs}
        non_sub = sources - SUBLEDGER_SOURCES
        if len(legs) >= 2 and non_sub and len(sources) == 1:
            exc.append(f"SELF-CLEARED — invoice {ref}: both legs posted by single "
                      f"non-subledger source {sources}")
    return {
        "id": "C21", "name": "Segregation of duties — single-source prepare-and-pay (proxy)",
        "objective": "No single source both raises and clears an AR receivable. Uses the "
                     "GL Source field as a preparer/approver proxy (see limitations — "
                     "Source is not a user ID).",
        "assertion": "existence/occurrence", "delivery": "EVIDENCED",
        "result": _result(None, len(exc)),
        "detail": f"{len(exc)} self-cleared item(s) for review",
        "exceptions": exc[:25],
    }


def run_controls(data_dir=None):
    """Run the full AR controls register. Returns dict with register + counts."""
    d = data_dir or D
    aging = load("AR_Aging.csv", d)
    gl = load("GL.csv", d)
    if not aging or not gl:
        raise ValueError("AR_Aging.csv and GL.csv must exist and be non-empty in " + d)

    # Validate schema — key columns required for controls
    if aging and not any("Invoice_Number" in row for row in aging[:1]):
        raise ValueError("AR_Aging.csv missing Invoice_Number column")
    if gl and not any("Account_Number" in row for row in gl[:1]):
        raise ValueError("GL.csv missing Account_Number column")

    register = [
        c2_gl_posting_hygiene(gl),
        c4_duplicate_keys(aging, gl),
        c5_referential_integrity(aging, gl),
        c8_manual_je_to_ar_control(gl, aging),
        c9_two_way_coverage(aging, gl),
        c10_cutoff_integrity(gl),
        c_r1_allowance_adequacy(gl, d),
        c21_segregation_of_duties(gl),
    ]
    fails = sum(1 for c in register if c["result"] == "FAIL")
    reviews = sum(1 for c in register if c["result"] == "REVIEW")
    return {"register": register, "fail_count": fails, "review_count": reviews}


if __name__ == "__main__":
    r = run_controls()
    print("AR CONTROLS REGISTER — close", CLOSE_PERIOD, "(SYNTHETIC)\n")
    for c in r["register"]:
        tag = {"PASS": "[PASS]", "FAIL": "[FAIL]",
               "REVIEW": "[REVIEW]", "OK": "[OK]"}[c["result"]]
        print(f"{tag} {c['id']} {c['name']}")
        print(f"        assertion: {c['assertion']} | {c['delivery']} | {c['detail']}")
        for e in c["exceptions"][:5]:
            print(f"          - {e}")
        if len(c["exceptions"]) > 5:
            print(f"          ... ({len(c['exceptions']) - 5} more)")
    print(f"\nSUMMARY: {r['fail_count']} FAIL, {r['review_count']} REVIEW, "
          f"{len(r['register']) - r['fail_count'] - r['review_count']} PASS/OK")
    print("CONTROLS PASS — ready for controller sign-off" if r["fail_count"] == 0
          else "** CONTROL FAILURES — resolve before sign-off **")
