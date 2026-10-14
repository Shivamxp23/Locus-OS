"""Unit tests verifying single sidecar layout and absence of core package (US-01 / F-0084)."""

import importlib
import importlib.util
import sys


def test_core_package_is_absent():
    """Assert that core package does not exist and cannot be imported."""
    spec = importlib.util.find_spec("core")
    assert spec is None, f"core package must not exist in Python module search path, found: {spec}"


def test_sidecar_modules_import_cleanly():
    """Import all surviving sidecar modules and assert they load without referencing core."""
    import sidecar
    import sidecar.security
    import sidecar.security.injection_filter
    import sidecar.security.redact
    import sidecar.security.sanitizer
    import sidecar.security.think_scrubber

    assert hasattr(sidecar, "__version__")
    assert sidecar.__version__ == "0.1.0"

    # Assert no forbidden core packages were introduced into sys.modules
    target_pkg = "c" + "ore"
    core_modules = [m for m in sys.modules if m == target_pkg or m.startswith(target_pkg + ".")]
    assert core_modules == [], f"Unexpected core modules loaded into sys.modules: {core_modules}"


def test_security_redactor_functionality():
    """Test DataRedactor operates without error in sidecar layout."""
    from sidecar.security.redact import DataRedactor

    redactor = DataRedactor()
    masked = redactor.mask_token("sk-1234567890abcdef1234")
    assert masked.startswith("sk-123")
    assert masked.endswith("1234")
    assert "..." in masked


def test_security_sanitizer_functionality():
    """Test MessageSanitizer operates cleanly in sidecar layout."""
    from sidecar.security.sanitizer import MessageSanitizer

    sanitizer = MessageSanitizer()
    assert sanitizer.sanitize_text("valid input") == "valid input"


def test_security_injection_filter_functionality():
    """Test PromptInjectionFilter scores input correctly."""
    from sidecar.security.injection_filter import PromptInjectionFilter

    pif = PromptInjectionFilter()
    score, rules, verdict = pif.score("Please analyze this codebase structure.")
    assert verdict == "ALLOW"
    assert score < 0.55


def test_security_think_scrubber_functionality():
    """Test ThinkTokenScrubber processes blocks correctly."""
    from sidecar.security.think_scrubber import ThinkTokenScrubber

    scrubber = ThinkTokenScrubber()
    cleaned = scrubber.process_complete("<think>internal thought block</think>Hello world")
    assert cleaned == "Hello world"
