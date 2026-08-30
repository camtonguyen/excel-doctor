import shutil
import tempfile
from pathlib import Path

from backend.audit.rules_display import RuleR11, RuleR17, RuleR18, RuleR19
from backend.model import CellModel, SheetModel, WorkbookInventory
from backend.workbook.reader import WorkbookModel, read_workbook
from backend.workbook.xml_patcher import apply_edits

R11_FIXTURE_PATH = (
    Path(__file__).parent.parent.parent.parent / "fixtures" / "r11_date_serial.xlsx"
)



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
            },
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
            },
        )
    }
    findings = rule.detect(wb_safe)
    assert len(findings) == 0


def test_r18_fragile_format_codes():
    rule = RuleR18()

    wb = WorkbookModel(inventory=WorkbookInventory())
    wb.sheets = {
        "Sheet1": SheetModel(
            name="Sheet1",
            target="worksheets/sheet1.xml",
            cells={
                "A1": CellModel(ref="A1", v="100", num_fmt="#,##0.00_);\\(#,##0.00\\)"),
                "A2": CellModel(ref="A2", v="100", num_fmt="[$-409]dd/mm/yyyy"),
                "A3": CellModel(ref="A3", v="-100", num_fmt="#,##0.00;[Red]-#,##0.00"),
                "A4": CellModel(ref="A4", v="100", num_fmt="0.00"),  # safe
            },
        )
    }
    findings = rule.detect(wb)
    assert len(findings) == 3

    # A1 fix
    f_a1 = next(f for f in findings if f.ref == "A1")
    edits_a1 = rule.fix(wb, f_a1)
    assert edits_a1[0].num_fmt_code == "#,##0.00;(#,##0.00)"

    # A2 fix
    f_a2 = next(f for f in findings if f.ref == "A2")
    edits_a2 = rule.fix(wb, f_a2)
    assert edits_a2[0].num_fmt_code == "dd/mm/yyyy"

    # A3 fix
    f_a3 = next(f for f in findings if f.ref == "A3")
    edits_a3 = rule.fix(wb, f_a3)
    assert edits_a3[0].num_fmt_code == "#,##0.00;-#,##0.00"


def test_r19_inconsistent_fonts():
    rule = RuleR19()

    wb = WorkbookModel(inventory=WorkbookInventory())
    cells = {}

    # Create 199 cells with Arial 11 (the majority)
    for i in range(1, 200):
        cells[f"A{i}"] = CellModel(
            ref=f"A{i}", v="text", font_name="Arial", font_size="11"
        )

    # Create 1 cell with a minority font (this is < 1% of the 100 cells)
    cells["B1"] = CellModel(ref="B1", v="text", font_name="Calibri", font_size="10")

    wb.sheets = {
        "Sheet1": SheetModel(name="Sheet1", target="worksheets/sheet1.xml", cells=cells)
    }

    findings = rule.detect(wb)
    assert len(findings) == 1
    assert findings[0].ref == "B1"

    edits = rule.fix(wb, findings[0])
    assert len(edits) == 1
    assert edits[0].op == "SetFont"
    assert edits[0].font_name == "Arial"
    assert edits[0].font_size == "11"


def test_r11_date_rendered_as_serial_detection_and_fix():
    wb = read_workbook(R11_FIXTURE_PATH)
    r11 = RuleR11()

    findings = r11.detect(wb)
    refs = {f.ref for f in findings}
    assert refs == {"B2", "B3", "C2", "C3"}
    assert all(f.rule_id == "R11" for f in findings)
    assert all(f.risk == "display" for f in findings)
    assert all(f.severity == "warning" for f in findings)

    findings_map = {f.ref: f for f in findings}
    for ref in ["B2", "B3", "C2", "C3"]:
        edits = r11.fix(wb, findings_map[ref])
        assert len(edits) == 1
        assert edits[0].op == "SetNumFmt"
        assert edits[0].sheet == "Sheet1"
        assert edits[0].ref == ref
        assert edits[0].num_fmt_code == "dd/mm/yyyy"


def test_r11_apply_fix_and_redetect():
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_in, tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as tmp_out:
        tmp_in_path = Path(tmp_in.name)
        tmp_out_path = Path(tmp_out.name)
    try:
        shutil.copy(R11_FIXTURE_PATH, tmp_in_path)
        wb = read_workbook(tmp_in_path)
        r11 = RuleR11()
        findings = r11.detect(wb)
        assert len(findings) == 4

        all_edits = []
        for f in findings:
            all_edits.extend(r11.fix(wb, f))

        apply_edits(tmp_in_path, tmp_out_path, all_edits)

        wb_fixed = read_workbook(tmp_out_path)
        findings_after = r11.detect(wb_fixed)
        assert len(findings_after) == 0
    finally:
        if tmp_in_path.exists():
            tmp_in_path.unlink()
        if tmp_out_path.exists():
            tmp_out_path.unlink()

