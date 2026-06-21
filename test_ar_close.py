"""
AR close engine — regression tests.
Expected values are the verified outputs from running against the included
synthetic data (AR_Aging.csv + GL.csv).  All figures verified to the cent.

Run:  pytest test_ar_close.py -v
"""
import pytest
from ar_close import run_close
from ar_review import compute_truth, run_review
from ar_controls import run_controls


@pytest.fixture(scope="module")
def close_result():
    return run_close()


@pytest.fixture(scope="module")
def truth():
    return compute_truth()


# ── ar_close.py ──────────────────────────────────────────────────────────────

class TestSubledger:
    def test_total(self, close_result):
        assert abs(close_result["subledger"] - 26_713_341.80) < 0.01

    def test_aging_buckets_sum_to_subledger(self, close_result):
        bucket_total = sum(v["open"] for v in close_result["agesum"].values())
        assert abs(bucket_total - close_result["subledger"]) < 0.01


class TestReserve:
    def test_required_reserve(self, close_result):
        assert abs(close_result["reserve"] - 1_613_173.40) < 0.01

    def test_nrv(self, close_result):
        assert abs(close_result["nrv"] - 25_100_168.40) < 0.01

    def test_nrv_positive(self, close_result):
        assert close_result["nrv"] > 0

    def test_nrv_formula(self, close_result):
        assert abs(close_result["nrv"] - (close_result["subledger"] - close_result["reserve"])) < 0.01

    def test_disputed_excluded_from_reserve(self, close_result):
        # reserve base must be < subledger (disputed + credit invoices excluded)
        reserve_base_total = sum(close_result["resbase"].values())
        assert reserve_base_total < close_result["subledger"]


class TestGLReconciliation:
    def test_gl_ar_balance(self, close_result):
        assert abs(close_result["gl_ar"] - 26_711_691.80) < 0.01

    def test_variance(self, close_result):
        assert abs(close_result["variance"] - (-1_650.00)) < 0.01

    def test_residual_zero(self, close_result):
        """Flagged breaks must fully explain the variance — residual must be 0."""
        assert abs(close_result["residual"]) < 0.01

    def test_auto_items_count(self, close_result):
        """3 GL entries posted to AR-1200 with no invoice reference."""
        assert len(close_result["auto_items"]) == 3


class TestControlChecks:
    def test_all_controls_pass(self, close_result):
        failures = [(name, detail) for name, detail, ok in close_result["checks"] if not ok]
        assert failures == [], f"Control failures: {failures}"

    def test_exactly_five_controls(self, close_result):
        assert len(close_result["checks"]) == 5

    def test_gl_balanced(self, close_result):
        name, detail, ok = close_result["checks"][0]
        assert ok, f"GL balanced check failed: {detail}"

    def test_aging_sum_control(self, close_result):
        name, detail, ok = close_result["checks"][1]
        assert ok, f"Aging sum control failed: {detail}"

    def test_recon_ties(self, close_result):
        name, detail, ok = close_result["checks"][2]
        assert ok, f"Recon tie check failed: {detail}"


# ── ar_review.py — planted error detection ───────────────────────────────────

class TestReviewTruth:
    def test_truth_subledger(self, truth):
        assert abs(truth["subledger total"] - 26_713_341.80) < 0.01

    def test_truth_reserve(self, truth):
        assert abs(truth["required reserve"] - 1_613_173.40) < 0.01

    def test_truth_nrv(self, truth):
        assert abs(truth["net realizable"] - 25_100_168.40) < 0.01


class TestPlantedErrors:
    """ar_review.py must catch both planted mistakes in AR_Close_Prepared_SAMPLE.xlsx."""

    @pytest.fixture(scope="class")
    @staticmethod
    def review_rows():
        rows, _ = run_review()
        return {m: (g, e, res, diag) for m, g, e, res, diag in rows}

    def test_subledger_double_count_detected(self, review_rows):
        """Preparer doubled the subledger total — reviewer must flag it FAIL."""
        _, _, result, _ = review_rows["subledger total"]
        assert result == "FAIL"

    def test_subledger_double_count_diagnosis(self, review_rows):
        _, _, _, diag = review_rows["subledger total"]
        assert "double" in diag.lower() or "2x" in diag.lower()

    def test_true_up_sign_flip_detected(self, review_rows):
        """Preparer added opening allowance instead of subtracting — must flag FAIL."""
        _, _, result, _ = review_rows["true-up"]
        assert result == "FAIL"

    def test_true_up_sign_flip_diagnosis(self, review_rows):
        _, _, _, diag = review_rows["true-up"]
        assert "sign" in diag.lower() or "adding" in diag.lower() or "subtracting" in diag.lower()

    def test_correct_fields_pass(self, review_rows):
        """GL AR control and required reserve are correct in the sample — must pass."""
        for field in ("gl ar control", "required reserve"):
            _, _, result, _ = review_rows[field]
            assert result == "OK", f"Expected {field} to pass but got {result}"

    def test_total_fails(self):
        _, fails = run_review()
        assert fails >= 2


# ── ar_controls.py — SOX-style controls register ──────────────────────────────

class TestControlsRegister:
    @pytest.fixture(scope="class")
    @staticmethod
    def reg():
        return run_controls()

    def test_register_has_eight_controls(self, reg):
        assert len(reg["register"]) == 8

    def test_manual_je_to_ar_control_detected(self, reg):
        c8 = next(c for c in reg["register"] if c["id"] == "C8")
        assert c8["result"] == "FAIL"
        assert "1,650" in c8["detail"] or "−1,650" in c8["detail"]

    def test_manual_je_flag_names_source(self, reg):
        c8 = next(c for c in reg["register"] if c["id"] == "C8")
        assert any("Manual JE" in e or "Entry" in e for e in c8["exceptions"])

    def test_under_reserved_detected(self, reg):
        c_r1 = next(c for c in reg["register"] if c["id"] == "C-R1")
        assert c_r1["result"] == "FAIL"
        assert "reserve" in c_r1["detail"].lower()

    def test_clean_data_passes_integrity_controls(self, reg):
        integrity = {c["id"]: c["result"] for c in reg["register"]
                     if c["id"] in ("C2", "C4", "C5", "C10")}
        assert all(r == "PASS" for r in integrity.values())

    def test_evidenced_controls_report_ok_or_review(self, reg):
        evidenced = {c["id"]: c["result"] for c in reg["register"]
                     if c["delivery"] == "EVIDENCED"}
        assert all(r in ("OK", "REVIEW") for r in evidenced.values())

    def test_two_failures_total(self, reg):
        assert reg["fail_count"] == 2

    def test_every_control_has_objective_and_assertion(self, reg):
        for c in reg["register"]:
            assert c["objective"] and len(c["objective"]) > 10
            assert c["assertion"] and c["assertion"] in (
                "accuracy/valuation", "existence/occurrence", "completeness", "cutoff")
