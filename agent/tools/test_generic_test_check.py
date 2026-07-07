"""Unit tests for the regression-check parsing/diffing logic. Run with:
    pytest agent/tools/test_generic_test_check.py -v
No subprocess/network/API calls -- pure function tests against hand-written
fake pytest -v output.
"""

from .generic_test_check import diff_test_results, parse_pytest_verbose_output

_FAKE_PYTEST_V_OUTPUT_BEFORE = """\
============================= test session starts ==============================
collected 3 items

tests/test_a.py::test_one PASSED                                        [ 33%]
tests/test_a.py::test_two FAILED                                        [ 66%]
tests/test_b.py::test_three PASSED                                      [100%]

=================================== FAILURES ===================================
"""

_FAKE_PYTEST_V_OUTPUT_AFTER_CLEAN_FIX = """\
============================= test session starts ==============================
collected 3 items

tests/test_a.py::test_one PASSED                                        [ 33%]
tests/test_a.py::test_two PASSED                                        [ 66%]
tests/test_b.py::test_three PASSED                                      [100%]
"""

_FAKE_PYTEST_V_OUTPUT_AFTER_REGRESSION = """\
============================= test session starts ==============================
collected 3 items

tests/test_a.py::test_one PASSED                                        [ 33%]
tests/test_a.py::test_two PASSED                                        [ 66%]
tests/test_b.py::test_three FAILED                                      [100%]
"""


def test_parse_pytest_verbose_output():
    parsed = parse_pytest_verbose_output(_FAKE_PYTEST_V_OUTPUT_BEFORE)
    assert parsed == {
        "tests/test_a.py::test_one": "PASSED",
        "tests/test_a.py::test_two": "FAILED",
        "tests/test_b.py::test_three": "PASSED",
    }


def test_diff_test_results_clean_fix_no_regressions():
    before = parse_pytest_verbose_output(_FAKE_PYTEST_V_OUTPUT_BEFORE)
    after = parse_pytest_verbose_output(_FAKE_PYTEST_V_OUTPUT_AFTER_CLEAN_FIX)
    diff = diff_test_results(before, after)
    assert diff["regressions"] == []
    assert diff["newly_fixed"] == ["tests/test_a.py::test_two"]


def test_diff_test_results_detects_introduced_regression():
    before = parse_pytest_verbose_output(_FAKE_PYTEST_V_OUTPUT_BEFORE)
    after = parse_pytest_verbose_output(_FAKE_PYTEST_V_OUTPUT_AFTER_REGRESSION)
    diff = diff_test_results(before, after)
    assert diff["regressions"] == ["tests/test_b.py::test_three"]
    assert diff["newly_fixed"] == ["tests/test_a.py::test_two"]
