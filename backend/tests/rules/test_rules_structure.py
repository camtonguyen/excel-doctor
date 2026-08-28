from backend.audit.rules_structure import (
    RuleR15,
    RuleR21,
    _generate_safe_name,
    _is_invalid,
)
from backend.model import CellModel, SheetModel
from backend.workbook.reader import WorkbookModel


def test_is_invalid():
    assert _is_invalid("ValidName") is False
    assert _is_invalid("Name With Spaces") is False
    assert _is_invalid("  Leading Space") is True
    assert _is_invalid("Trailing Space  ") is True
    assert _is_invalid("Contains[Bracket]") is True
    assert _is_invalid("Contains/Slash") is True
    assert _is_invalid("Contains?Mark") is True
    assert _is_invalid("A" * 32) is True
    assert _is_invalid("Contains,Comma") is True
    assert _is_invalid("Contains.Period") is True
    assert _is_invalid("Contains'Apostrophe") is True


def test_generate_safe_name():
    wb = WorkbookModel(inventory=None)
    wb.sheets = {
        "Sheet1": SheetModel(name="Sheet1", target=""),
        "Sheet2": SheetModel(name="Sheet2", target=""),
    }

    assert _generate_safe_name(wb, "  Sheet 3  ") == "Sheet 3"
    assert _generate_safe_name(wb, "Invalid[Name]") == "Invalid_Name"

    # Truncation
    assert len(_generate_safe_name(wb, "A" * 50)) == 31

    # Empty after strip
    assert _generate_safe_name(wb, ".,.,.,") == "Sheet"

    # Collision
    assert _generate_safe_name(wb, "Sheet[1]") == "Sheet_1"
    wb.sheets["Sheet_1"] = SheetModel(name="Sheet_1", target="")
    assert _generate_safe_name(wb, "Sheet[1]") == "Sheet_1 1"


def test_rule_r15_detect_and_fix():
    wb = WorkbookModel(inventory=None)
    wb.sheets = {
        "Valid Sheet": SheetModel(name="Valid Sheet", target=""),
        "Bad[Sheet]": SheetModel(name="Bad[Sheet]", target=""),
        "A" * 35: SheetModel(name="A" * 35, target=""),
    }

    rule = RuleR15()
    findings = rule.detect(wb)

    assert len(findings) == 2
    assert findings[0].sheet == "Bad[Sheet]"
    assert findings[1].sheet == "A" * 35

    edits1 = rule.fix(wb, findings[0])
    assert len(edits1) == 1
    assert edits1[0].op == "RenameSheet"
    assert edits1[0].new_name == "Bad_Sheet"

    edits2 = rule.fix(wb, findings[1])
    assert len(edits2) == 1
    assert edits2[0].new_name == "A" * 31

def test_r21_bloated_used_range():
    rule = RuleR21()
    wb = WorkbookModel(inventory=None)
    
    cells2 = {
        "A1": CellModel(ref="A1", v="1"),
        "B2": CellModel(ref="B2", v="2"),
    }
    
    cells3 = {
        "A1": CellModel(ref="A1", v="1"),
        "C3": CellModel(ref="C3", v="3"),
    }
    
    wb.sheets = {
        "Empty": SheetModel(name="Empty", target="", cells={}, dimension="A1:Z100"),
        "Bloated": SheetModel(name="Bloated", target="", cells=cells2, dimension="A1:Z102"),
        "Good": SheetModel(name="Good", target="", cells=cells3, dimension="A1:C3"),
    }
    
    findings = rule.detect(wb)
    assert len(findings) == 2
    sheets = {f.sheet for f in findings}
    assert sheets == {"Empty", "Bloated"}
    
    f_empty = next(f for f in findings if f.sheet == "Empty")
    edits_empty = rule.fix(wb, f_empty)
    assert edits_empty[0].op == "SetDimension"
    assert edits_empty[0].dimension == "A1"
    
    f_bloated = next(f for f in findings if f.sheet == "Bloated")
    edits_bloated = rule.fix(wb, f_bloated)
    assert edits_bloated[0].op == "SetDimension"
    assert edits_bloated[0].dimension == "A1:B2"
