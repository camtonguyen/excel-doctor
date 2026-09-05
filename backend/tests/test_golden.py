import json
import tempfile
from pathlib import Path

import pytest

from backend.audit.rules_datatype import RuleR14
from backend.audit.rules_display import RuleR11
from backend.model import CellEdit
from backend.verify.verifier import compute_diff
from backend.workbook.reader import read_workbook
from backend.workbook.xml_patcher import apply_edits

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"
GOLDEN_DIR = Path(__file__).parent / "golden"

GOLDEN_TESTS = [
    ("whitespace.xlsx", RuleR14(), "whitespace.after.xlsx", "whitespace.diff.json"),
    (
        "r11_date_serial.xlsx",
        RuleR11(),
        "r11_date_serial.after.xlsx",
        "r11_date_serial.diff.json",
    ),
]


@pytest.mark.parametrize(
    "src_name, rule, golden_xlsx_name, golden_diff_name", GOLDEN_TESTS
)
def test_golden_file_parity(src_name, rule, golden_xlsx_name, golden_diff_name):
    """
    Spec §7 Golden files:
    For the end-to-end path, commit golden/<fixture>.after.xlsx and golden/<fixture>.diff.json
    next to each input. The test repairs the input with a fixed fix-set and asserts
    the result matches the golden pair.
    """
    src_path = FIXTURES_DIR / src_name
    golden_xlsx = GOLDEN_DIR / golden_xlsx_name
    golden_diff = GOLDEN_DIR / golden_diff_name

    assert src_path.exists()
    assert golden_xlsx.exists()
    assert golden_diff.exists()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_out = Path(tmp_dir) / "patched.xlsx"

        wb = read_workbook(src_path)
        findings = rule.detect(wb)
        edits: list[CellEdit] = []
        for f in findings:
            edits.extend(rule.fix(wb, f))

        apply_edits(src_path, tmp_out, edits)
        diffs = compute_diff(src_path, tmp_out, edits, findings)

        # 1. Assert diff matches golden diff.json exactly
        with open(golden_diff, "r", encoding="utf-8") as f:
            expected_diff_data = json.load(f)

        actual_diff_data = sorted(
            [d.__dict__ for d in diffs], key=lambda x: (x["sheet"], x["ref"])
        )
        assert actual_diff_data == expected_diff_data

        # 2. Assert patched workbook matches golden workbook model
        wb_actual = read_workbook(tmp_out)
        wb_golden = read_workbook(golden_xlsx)

        assert len(wb_actual.sheets) == len(wb_golden.sheets)
        for sheet_name in wb_actual.sheets:
            sheet_actual = wb_actual.sheets[sheet_name]
            sheet_golden = wb_golden.sheets[sheet_name]

            assert len(sheet_actual.cells) == len(sheet_golden.cells)
            for ref, cell_act in sheet_actual.cells.items():
                cell_gld = sheet_golden.cells[ref]
                assert cell_act.v == cell_gld.v
                assert cell_act.f == cell_gld.f
                assert cell_act.t == cell_gld.t
                assert cell_act.num_fmt == cell_gld.num_fmt
