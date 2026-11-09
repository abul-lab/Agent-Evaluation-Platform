"""Unit tests for SecretExposureEvaluator."""

from pathlib import Path

from app.domain.models import CanonicalTrace
from app.evaluators.base import FindingSeverity
from app.evaluators.secret_scanner import SecretExposureEvaluator

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_trace(filename: str) -> CanonicalTrace:
    """Helper to load a CanonicalTrace from fixtures."""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return CanonicalTrace.model_validate_json(f.read())


def test_clean_trace_has_no_secret_exposure() -> None:
    """Verify clean_success_trace raises 0 secret exposure findings."""
    trace = load_trace("clean_success_trace.json")
    evaluator = SecretExposureEvaluator()
    findings = evaluator.evaluate(trace)

    assert len(findings) == 0


def test_secret_leak_trace_detected() -> None:
    """Verify secret_leak_trace flags SECRET_EXPOSURE with CRITICAL severity."""
    trace = load_trace("secret_leak_trace.json")
    evaluator = SecretExposureEvaluator()
    findings = evaluator.evaluate(trace)

    assert len(findings) >= 1
    for finding in findings:
        assert finding.code == "SECRET_EXPOSURE"
        assert finding.severity == FindingSeverity.CRITICAL
        # Must not log full secret; verify redaction
        assert "..." in finding.metadata["redacted_sample"]


def test_github_token_and_jwt_detected() -> None:
    """Verify scanner catches GitHub token and JWT patterns."""
    trace = load_trace("clean_success_trace.json")
    trace.steps[0].output_state = {
        "gh_token": "ghp_123456789012345678901234567890123456",
        "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgN_p_example_signature_99182371",
    }

    evaluator = SecretExposureEvaluator()
    findings = evaluator.evaluate(trace)

    codes = [f.code for f in findings]
    assert "SECRET_EXPOSURE" in codes
    assert any(f.metadata.get("pattern_name") == "GITHUB_TOKEN" for f in findings)
    assert any(f.metadata.get("pattern_name") == "JSON_WEB_TOKEN" for f in findings)


def test_stripe_style_live_key_detected() -> None:
    """Verify scanner catches Stripe-style live keys.

    The key is assembled at runtime so the repository never contains a literal
    live-key-shaped string (which secret scanners would flag).
    """
    trace = load_trace("clean_success_trace.json")
    stripe_style_key = "sk_" + "live_" + "A1b2C3d4E5f6G7h8I9j0K1l2"
    trace.steps[0].output_state = {"payment_api_key": stripe_style_key}

    findings = SecretExposureEvaluator().evaluate(trace)

    assert any(f.metadata.get("pattern_name") == "STRIPE_SECRET_KEY" for f in findings)
    assert all(stripe_style_key not in f.message for f in findings)
