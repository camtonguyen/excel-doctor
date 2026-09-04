from pathlib import Path

from backend.audit.base import registry
from backend.audit.rules_formula import (
    RuleR01,
    RuleR02,
    RuleR03,
    RuleR04,
    RuleR05,
    RuleR06,
    RuleR07,
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


def test_r07_empty_cell_breaks_chain():
    rule = RuleR07()
    wb = WorkbookModel(inventory=None)

    cells = {
        "A1": CellModel(ref="A1", f="B1+C1"),
        # A2 is completely missing
        "A3": CellModel(ref="A3", f="B3+C3"),
        "B1": CellModel(ref="B1", f="D1*2"),
        "B2": CellModel(ref="B2", v="10"),  # hardcoded value -> no gap
        "B3": CellModel(ref="B3", f="D3*2"),
        "C1": CellModel(ref="C1", f="E1-1"),
        "C2": CellModel(ref="C2", f=""),  # empty string formula -> gap
        "C3": CellModel(ref="C3", f="E3-1"),
    }

    wb.sheets = {"Sheet1": SheetModel(name="Sheet1", target="", cells=cells)}

    findings = rule.detect(wb)
    assert len(findings) == 2
    refs = {f.ref for f in findings}
    assert refs == {"A2", "C2"}

    # Fix for A2 uses A3's formula "B3+C3" shifted up to "B2+C2"
    fa2 = next(f for f in findings if f.ref == "A2")
    ea2 = rule.fix(wb, fa2)
    assert len(ea2) == 1
    assert ea2[0].formula == "B2+C2"

    # Fix for C2 uses C3's formula "E3-1" shifted up to "E2-1"
    fc2 = next(f for f in findings if f.ref == "C2")
    ec2 = rule.fix(wb, fc2)
    assert ec2[0].formula == "E2-1"


def test_r08_formula_outlier():
    from backend.audit.rules_formula import RuleR08
    from backend.workbook.reader import read_workbook

    wb = read_workbook("fixtures/r08_outlier.xlsx")
    rule = RuleR08()
    findings = rule.detect(wb)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.ref == "C4"

    # Test fix
    edits = rule.fix(wb, finding)
    assert len(edits) == 1
    assert edits[0].ref == "C4"
    assert edits[0].formula == "A4*B4"


def test_r03_error_code_literal_fix():
    r03 = RuleR03()
    wb = WorkbookModel(inventory=WorkbookInventory())
    wb.shared_strings = ["#REF!", "Normal text"]
    wb.sheets = {
        "Sheet1": SheetModel(
            name="Sheet1",
            target="worksheets/sheet1.xml",
            cells={
                "A1": CellModel(ref="A1", t="s", v="0"),  # points to #REF!
                "A2": CellModel(ref="A2", t="s", v="1"),  # normal
                "A3": CellModel(ref="A3", v="#DIV/0!"),  # direct literal
            },
        )
    }
    findings = r03.detect(wb)
    assert len(findings) == 2
    f_a1 = next(f for f in findings if f.ref == "A1")
    edits_a1 = r03.fix(wb, f_a1)
    assert len(edits_a1) == 1
    assert edits_a1[0].op == "ClearCell"
    assert edits_a1[0].ref == "A1"
    assert edits_a1[0].sheet == "Sheet1"

    f_a3 = next(f for f in findings if f.ref == "A3")
    edits_a3 = r03.fix(wb, f_a3)
    assert len(edits_a3) == 1
    assert edits_a3[0].op == "ClearCell"
    assert edits_a3[0].ref == "A3"


def test_r04_arithmetic_empty_cell_fix():
    r04 = RuleR04()
    wb = WorkbookModel(inventory=WorkbookInventory())
    wb.sheets = {
        "Sheet1": SheetModel(
            name="Sheet1",
            target="worksheets/sheet1.xml",
            cells={
                "A1": CellModel(ref="A1", t="str", v=""),  # empty string cell
                "B1": CellModel(ref="B1", f="A1*2"),  # arithmetic on A1
                "C1": CellModel(ref="C1", f="A1+B1"),  # arithmetic on A1
            },
        )
    }
    findings = r04.detect(wb)
    assert len(findings) == 2

    f_b1 = next(f for f in findings if f.ref == "B1")
    edits_b1 = r04.fix(wb, f_b1)
    assert len(edits_b1) == 1
    assert edits_b1[0].op == "SetFormula"
    assert edits_b1[0].ref == "B1"
    assert edits_b1[0].formula == "N(A1)*2"

    f_c1 = next(f for f in findings if f.ref == "C1")
    edits_c1 = r04.fix(wb, f_c1)
    assert len(edits_c1) == 1
    assert edits_c1[0].formula == "N(A1)+B1"

