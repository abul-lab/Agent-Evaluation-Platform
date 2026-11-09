"""CSV export safety: spreadsheet formula injection is neutralized."""

import pytest

from app.services.report_service import csv_safe


@pytest.mark.parametrize(
    "value", ['=HYPERLINK("http://x")', "+cmd", "-2+3", "@SUM(A1)", "\tcmd", "\rcmd"]
)
def test_formula_prefixes_are_quoted(value: str) -> None:
    assert csv_safe(value) == "'" + value


@pytest.mark.parametrize("value", ["plain message", "[1, 2]", "", 7, None])
def test_safe_values_are_unchanged(value: object) -> None:
    assert csv_safe(value) == value
