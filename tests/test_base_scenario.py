from __future__ import annotations

# delegation-guard: ok — tests for _submit_verified (irreversible-action gate), authored by the contract owner
import asyncio
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


# ---------------------------------------------------------------------------
# _submit_verified — pre-submit self-verify gate (irreversible actions)
# delegation-guard: ok — contract owner authoring tests for own new method
# Contract: the irreversible click (_submit_and_check) happens IFF the gate
# passes. On any gate failure it returns (False, checks) WITHOUT clicking, and
# checks["_gate"] names the reason.
# ---------------------------------------------------------------------------


class FakeLocator:
    """Stands in for a Playwright Locator. `.first` returns self."""

    def __init__(self, *, count=1, input_value=None, inner_text=None, raise_on_input=False):
        self._count = count
        self._input_value = input_value
        self._inner_text = inner_text
        self._raise_on_input = raise_on_input
        self.first = self

    async def count(self):
        return self._count

    async def input_value(self):
        if self._raise_on_input:
            raise RuntimeError("element is not an <input>/<textarea>")
        return self._input_value

    async def inner_text(self):
        return self._inner_text


class GatePage(MockPage):
    """MockPage that resolves locators from a dict and records screenshots."""

    def __init__(self, locators):
        super().__init__()
        self._locators = locators
        self.screenshot_calls = []

    def locator(self, selector):
        return self._locators[selector]

    async def screenshot(self, path, **kwargs):
        self.screenshot_calls.append(path)


def _gate_scenario(locators, submit_returns=True):
    """Build a BaseScenario whose _submit_and_check is stubbed to record calls."""
    page = GatePage(locators)
    sc = BaseScenario(page, "http://x", tmp_output_dir())
    calls = []

    async def fake_submit(loc):
        calls.append(loc)
        return submit_returns

    sc._submit_and_check = fake_submit  # seam: assert click happens only on gate pass
    return sc, calls, page


def test_submit_verified_passes_and_clicks():
    """All fields match → gate passes → _submit_and_check called once, ok=True."""
    submit = FakeLocator()
    locators = {
        "input[name='name']": FakeLocator(input_value="TITAN"),
        "input[name='phone']": FakeLocator(input_value="+357 99 000000"),
    }
    sc, calls, page = _gate_scenario(locators)

    ok, checks = asyncio.run(sc._submit_verified(
        submit_locator=submit,
        expect={"input[name='name']": "TITAN", "input[name='phone']": None},
        name="create",
    ))

    assert ok is True
    assert checks["_gate"] == "passed"
    assert len(calls) == 1           # irreversible click DID happen
    assert calls[0] is submit
    assert checks["input[name='name']"] == "TITAN"
    assert "_presubmit_screenshot" in checks
    assert len(page.screenshot_calls) == 1


def test_submit_verified_aborts_on_empty_required():
    """expected None + empty actual → gate aborts, NO click."""
    submit = FakeLocator()
    locators = {
        "input[name='name']": FakeLocator(input_value="TITAN"),
        "input[name='phone']": FakeLocator(input_value="   "),  # whitespace → stripped empty
    }
    sc, calls, _ = _gate_scenario(locators)

    ok, checks = asyncio.run(sc._submit_verified(
        submit_locator=submit,
        expect={"input[name='name']": "TITAN", "input[name='phone']": None},
        name="create",
    ))

    assert ok is False
    assert checks["_gate"] == "empty:input[name='phone']"
    assert calls == []               # irreversible click did NOT happen
    assert "_presubmit_screenshot" in checks  # evidence still captured on abort


def test_submit_verified_aborts_on_mismatch():
    """actual != expected → gate aborts, NO click."""
    submit = FakeLocator()
    locators = {"input[name='name']": FakeLocator(input_value="ACTUAL")}
    sc, calls, _ = _gate_scenario(locators)

    ok, checks = asyncio.run(sc._submit_verified(
        submit_locator=submit,
        expect={"input[name='name']": "EXPECTED"},
        name="create",
    ))

    assert ok is False
    assert checks["_gate"] == "mismatch:input[name='name']"
    assert calls == []


def test_submit_verified_aborts_on_missing_field():
    """locator count 0 → field_missing, NO click, value marked <missing>."""
    submit = FakeLocator()
    locators = {"input[name='gone']": FakeLocator(count=0)}
    sc, calls, _ = _gate_scenario(locators)

    ok, checks = asyncio.run(sc._submit_verified(
        submit_locator=submit,
        expect={"input[name='gone']": "anything"},
        name="create",
    ))

    assert ok is False
    assert checks["_gate"] == "field_missing:input[name='gone']"
    assert checks["input[name='gone']"] == "<missing>"
    assert calls == []


def test_submit_verified_inner_text_fallback_for_custom_select():
    """input_value() raising (non-input widget) → falls back to inner_text(); matches → passes.

    This is the custom-Select path the gate's None-expect is designed for.
    """
    submit = FakeLocator()
    locators = {
        "div[name='abuse_type']": FakeLocator(raise_on_input=True, inner_text="Arbitrage"),
    }
    sc, calls, _ = _gate_scenario(locators)

    ok, checks = asyncio.run(sc._submit_verified(
        submit_locator=submit,
        expect={"div[name='abuse_type']": None},  # must be non-empty
        name="create",
    ))

    assert ok is True
    assert checks["_gate"] == "passed"
    assert checks["div[name='abuse_type']"] == "Arbitrage"
    assert len(calls) == 1


def test_submit_verified_gate_pass_but_api_error_is_distinguishable():
    """Gate passes but _submit_and_check returns False (API 4xx/5xx).

    ok=False but _gate=='passed' — lets the caller tell 'submitted-with-error'
    apart from 'aborted-before-click'.
    """
    submit = FakeLocator()
    locators = {"input[name='name']": FakeLocator(input_value="TITAN")}
    sc, calls, _ = _gate_scenario(locators, submit_returns=False)

    ok, checks = asyncio.run(sc._submit_verified(
        submit_locator=submit,
        expect={"input[name='name']": "TITAN"},
        name="create",
    ))

    assert ok is False
    assert checks["_gate"] == "passed"   # NOT an abort reason
    assert len(calls) == 1               # the click DID happen


def test_submit_verified_first_failure_wins():
    """Multiple bad fields → gate reports the FIRST encountered (dict order)."""
    submit = FakeLocator()
    locators = {
        "input[name='a']": FakeLocator(input_value=""),        # empty (required)
        "input[name='b']": FakeLocator(input_value="WRONG"),   # mismatch
    }
    sc, calls, _ = _gate_scenario(locators)

    ok, checks = asyncio.run(sc._submit_verified(
        submit_locator=submit,
        expect={"input[name='a']": None, "input[name='b']": "RIGHT"},
        name="create",
    ))

    assert ok is False
    assert checks["_gate"] == "empty:input[name='a']"  # first field wins
    assert calls == []
