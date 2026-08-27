from backend.audit.rules_display import RuleR17
from backend.model import CellModel, SheetModel, WorkbookInventory
from backend.workbook.reader import WorkbookModel


def test_r17_locale_ambiguous_date_formats():
    rule = RuleR17()
    
    # Cases that SHOULD be flagged
    wb_flag = WorkbookModel(inventory=WorkbookInventory())
    wb_flag.sheets = {
        "Sheet1": SheetModel(
            name="Sheet1",
            target="worksheets/sheet1.xml",
            cells={
                "A1": CellModel(ref="A1", v="40000", num_fmt="mm-dd-yyyy"),
                "A2": CellModel(ref="A2", v="40000", num_fmt="m/d/yy h:mm"),
                "A3": CellModel(ref="A3", v="40000", num_fmt="[$-409]mm-dd;@"),
                "A4": CellModel(ref="A4", v="40000", num_fmt="[$-en-US]m/d/yy"),
            }
        )
    }
    findings = rule.detect(wb_flag)
    assert len(findings) == 4
    for i, ref in enumerate(["A1", "A2", "A3", "A4"]):
        f = findings[i]
        assert f.ref == ref
        assert f.rule_id == "R17"
        
        edits = rule.fix(wb_flag, f)
        assert len(edits) == 1
        assert edits[0].op == "SetNumFmt"
        assert edits[0].num_fmt_code == "dd/mm/yyyy"

def test_r17_ignores_safe_formats():
    rule = RuleR17()
    
    # Cases that SHOULD NOT be flagged
    wb_safe = WorkbookModel(inventory=WorkbookInventory())
    wb_safe.sheets = {
        "Sheet1": SheetModel(
            name="Sheet1",
            target="worksheets/sheet1.xml",
            cells={
                "B1": CellModel(ref="B1", v="40000", num_fmt="dd/mm/yyyy"),
                "B2": CellModel(ref="B2", v="40000", num_fmt="yyyy-mm-dd"),
                "B3": CellModel(ref="B3", v="40000", num_fmt="d-mmm-yy"),
                "B4": CellModel(ref="B4", v="40000", num_fmt="General"),
                "B5": CellModel(ref="B5", v="40000", num_fmt=None),
                "B6": CellModel(ref="B6", v="40000", num_fmt="[$-en-US]dd/mm/yyyy"),
            }
        )
    }
    findings = rule.detect(wb_safe)
    assert len(findings) == 0
