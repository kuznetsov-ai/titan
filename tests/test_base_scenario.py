from __future__ import annotations

import time

from scenarios.base import BaseScenario, StepResult


class MockPage:
    """Minimal mock that satisfies BaseScenario.__init__ (registers event callbacks)."""

    def __init__(self):
        self._handlers: dict[str, list] = {}

    def on(self, event: str, callback):
        self._handlers.setdefault(event, []).append(callback)


# ---------------------------------------------------------------------------
# StepResult
# ---------------------------------------------------------------------------


def test_step_result_dataclass():
    r = StepResult(
        name="load_page",
        status="PASS",
        description="Page loaded OK",
        screenshot_path="/tmp/shot.png",
        duration_ms=142,
        js_errors=["ReferenceError: x is not defined"],
        network_errors=["500 /api/cases"],
    )
    assert r.name == "load_page"
    assert r.status == "PASS"
    assert r.description == "Page loaded OK"
    assert r.screenshot_path == "/tmp/shot.png"
    assert r.duration_ms == 142
    assert r.js_errors == ["ReferenceError: x is not defined"]
    assert r.network_errors == ["500 /api/cases"]


def test_step_result_defaults():
    r = StepResult(name="x", status="FAIL", description="boom")
    assert r.screenshot_path is None
    assert r.duration_ms == 0
    assert r.js_errors == []
    assert r.network_errors == []


# ---------------------------------------------------------------------------
# BaseScenario
# ---------------------------------------------------------------------------


def test_record_appends_result():
    page = MockPage()
    sc = BaseScenario(page, "http://localhost:3000/", tmp_output_dir())
    assert sc.results == []

    start = time.monotonic()
    sc._record("step1", "PASS", "ok", "/tmp/s.png", start)
    assert len(sc.results) == 1
    assert sc.results[0].name == "step1"
    assert sc.results[0].status == "PASS"
    assert sc.results[0].duration_ms >= 0


def test_output_subdir():
    assert BaseScenario.OUTPUT_SUBDIR == "default"


def test_init_creates_output_dir(tmp_path):
    page = MockPage()
    sc = BaseScenario(page, "http://localhost:3000", tmp_path)
    expected = tmp_path / "default"
    assert expected.is_dir()
    assert sc.output_dir == expected


def test_init_registers_event_handlers():
    page = MockPage()
    BaseScenario(page, "http://localhost:3000", tmp_output_dir())
    assert "pageerror" in page._handlers
    assert "response" in page._handlers


def test_base_url_trailing_slash_stripped():
    page = MockPage()
    sc = BaseScenario(page, "http://localhost:3000/", tmp_output_dir())
    assert sc.base_url == "http://localhost:3000"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def tmp_output_dir():
    """Return a temporary Path that auto-cleans (used when tmp_path fixture is not available)."""
    import tempfile
    from pathlib import Path
    return Path(tempfile.mkdtemp())
