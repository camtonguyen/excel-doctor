from pathlib import Path

from backend.audit.rules_datatype import RuleR14
from backend.workbook.reader import read_workbook

FIXTURE_PATH = Path(__file__).parent.parent.parent.parent / "fixtures" / "whitespace.xlsx"


def test_r14_detects_every_whitespace_defect_and_skips_clean_text():
    wb = read_workbook(FIXTURE_PATH)
    r14 = RuleR14()

    findings = r14.detect(wb)

    refs = {f.ref for f in findings}
    assert refs == {"A1", "A2", "A3", "A4"}
    assert all(f.rule_id == "R14" for f in findings)


def test_r14_fix_returns_cleaned_text():
    wb = read_workbook(FIXTURE_PATH)
    r14 = RuleR14()
    findings = {f.ref: f for f in r14.detect(wb)}

    edits = r14.fix(wb, findings["A1"])
    assert len(edits) == 1
    assert edits[0].op == "SetValue"
    assert edits[0].sheet == "Sheet1"
    assert edits[0].ref == "A1"
    assert edits[0].value == "Doanh Thu"

    assert r14.fix(wb, findings["A2"])[0].value == "Doanh Thu"
    assert r14.fix(wb, findings["A3"])[0].value == "Doanh Thu"
    assert r14.fix(wb, findings["A4"])[0].value == "Doanh Thu"
