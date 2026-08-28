from pathlib import Path

from backend.audit.base import registry
from backend.audit.rules_formula import (
    RuleR01,
    RuleR02,
    RuleR03,
    RuleR04,
    RuleR05,
    RuleR06,
    RuleR20,
)
from backend.model import CellEdit, CellModel, SheetModel, WorkbookInventory
from backend.workbook.reader import WorkbookModel, read_workbook


def test_sokho_google_rules():
    fixture_path = (
        Path(__file__).parent.parent.parent.parent / "fixtures" / "sokho_google.xlsx"
    )
    wb = read_workbook(fixture_path)

    # R01: A2 formula contains #REF!
    r01 = RuleR01()
    findings_r01 = r01.detect(wb)
    assert len(findings_r01) == 1
    assert findings_r01[0].ref == "A2"
    assert findings_r01[0].rule_id == "R01"

    # R02: A2 (t="e") evaluates to error, B1 (v="#VALUE!") evaluates to error, A3 (v="#REF!")
    r02 = RuleR02()
    findings_r02 = r02.detect(wb)
    assert len(findings_r02) == 3
    refs = {f.ref for f in findings_r02}
    assert refs == {"A2", "B1", "A3"}

    # R03: B2 has t="s" and points to shared string #REF! (idx 0)
    r03 = RuleR03()
    findings_r03 = r03.detect(wb)
    assert len(findings_r03) == 1
    assert findings_r03[0].ref == "B2"

    # R04: B1 has formula A1*2, and A1 has t="str" v=""
    r04 = RuleR04()
    findings_r04 = r04.detect(wb)
    assert len(findings_r04) == 2
    refs_r04 = {f.ref for f in findings_r04}
    assert refs_r04 == {"B1", "A2"}

    # R05: A3 references 'Missing Sheet'
    r05 = RuleR05()
    findings_r05 = r05.detect(wb)
    assert len(findings_r05) == 1
    assert findings_r05[0].ref == "A3"

    # Registry test
    all_rules = registry.get_all()
    assert len(all_rules) >= 6


def test_r20_newer_excel_functions():
    rule = RuleR20()
    wb = WorkbookModel(inventory=WorkbookInventory())
    wb.sheets = {
        "Sheet1": SheetModel(
            name="Sheet1",
            target="worksheets/sheet1.xml",
            cells={
                "A1": CellModel(ref="A1", f="XLOOKUP(A2, B:B, C:C)"),
                "A2": CellModel(ref="A2", f="VLOOKUP(A3, B:C, 2, FALSE)"),  # safe
                "A3": CellModel(
                    ref="A3", f='IF(A4="XLOOKUP", 1, 0)'
                ),  # string literal should be ignored
                "A4": CellModel(ref="A4", f="filter(A:A, B:B>0)"),  # lowercase
            },
        )
    }

    findings = rule.detect(wb)
    assert len(findings) == 2
    refs = {f.ref for f in findings}
    assert refs == {"A1", "A4"}

    f_a1 = next(f for f in findings if f.ref == "A1")
    assert "XLOOKUP" in f_a1.description


def test_r06_running_balance_chain():
    rule = RuleR06()
    wb = WorkbookModel(inventory=None)

    # Needs at least 4 correctly linked cells.
    # We will make A2:A5 correctly linked. (4 cells)
    # A6 will be deviant (e.g. skips row 5, references A4).
    # A7 will be correct (references A6) but A6 broke it? Wait, links[r] == r-1 is all that matters.
    cells = {
        "A2": CellModel(ref="A2", f="A1+10"),
        "A3": CellModel(ref="A3", f="A2+10"),
        "A4": CellModel(ref="A4", f="A3+10"),
        "A5": CellModel(ref="A5", f="A4+10"),  # A2:A5 are 4 correctly linked
        "A6": CellModel(ref="A6", f="A4+10"),  # deviant, ref A4 instead of A5
        "A7": CellModel(ref="A7", f="A$5+10"),  # deviant, ref A$5 instead of A6
        "B2": CellModel(ref="B2", f="B1"),  # only 1 correct, not enough
    }

    wb.sheets = {"Sheet1": SheetModel(name="Sheet1", target="", cells=cells)}

    findings = rule.detect(wb)
    assert len(findings) == 2
    refs = {f.ref for f in findings}
    assert refs == {"A6", "A7"}

    f6 = next(f for f in findings if f.ref == "A6")
    edits6 = rule.fix(wb, f6)
    assert len(edits6) == 1
    assert isinstance(edits6[0], CellEdit)
    assert edits6[0].op == "SetFormula"
    assert edits6[0].formula == "A5+10"

    f7 = next(f for f in findings if f.ref == "A7")
    edits7 = rule.fix(wb, f7)
    assert edits7[0].formula == "A$6+10"
