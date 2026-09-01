import shutil
import tempfile
from pathlib import Path

from backend.audit.rules_datatype import RuleR09, RuleR10, RuleR12, RuleR13, RuleR14
from backend.workbook.reader import read_workbook
from backend.workbook.xml_patcher import apply_edits

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent.parent / "fixtures" / "whitespace.xlsx"
)
R09_FIXTURE_PATH = (
    Path(__file__).parent.parent.parent.parent / "fixtures" / "r09_number_as_text.xlsx"
)
R10_FIXTURE_PATH = (
    Path(__file__).parent.parent.parent.parent / "fixtures" / "r10_date_as_text.xlsx"
)
R12_FIXTURE_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "fixtures"
    / "r12_bool_percent_text.xlsx"
)
R13_FIXTURE_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "fixtures"
    / "r13_percent_wrong_scale.xlsx"
)



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


def test_r09_detects_numbers_stored_as_text():
    wb = read_workbook(R09_FIXTURE_PATH)
    r09 = RuleR09()

    findings = r09.detect(wb)
    refs = {f.ref for f in findings}
    assert refs == {"B2", "C2", "D2", "B3", "C3", "D3"}
    assert all(f.rule_id == "R09" for f in findings)
    assert all(f.risk == "value" for f in findings)
    assert all(f.severity == "warning" for f in findings)

    findings_map = {f.ref: f for f in findings}

    edits_b2 = r09.fix(wb, findings_map["B2"])
    assert len(edits_b2) == 1
    assert edits_b2[0].op == "SetValue"
    assert edits_b2[0].value == 15
    assert edits_b2[0].cell_type is None

    edits_c2 = r09.fix(wb, findings_map["C2"])
    assert edits_c2[0].value == 1500.5

    edits_d2 = r09.fix(wb, findings_map["D2"])
    assert edits_d2[0].value == 1234.56

    edits_c3 = r09.fix(wb, findings_map["C3"])
    assert edits_c3[0].value == -2.5

    edits_d3 = r09.fix(wb, findings_map["D3"])
    assert edits_d3[0].value == 2500000


def test_r09_apply_fix_and_redetect():
    with (
        tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_in,
        tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_out,
    ):
        tmp_in_path = Path(tmp_in.name)
        tmp_out_path = Path(tmp_out.name)
    try:
        shutil.copy(R09_FIXTURE_PATH, tmp_in_path)
        wb = read_workbook(tmp_in_path)
        r09 = RuleR09()
        findings = r09.detect(wb)
        assert len(findings) == 6

        all_edits = []
        for f in findings:
            all_edits.extend(r09.fix(wb, f))

        apply_edits(tmp_in_path, tmp_out_path, all_edits)

        wb_fixed = read_workbook(tmp_out_path)
        findings_after = r09.detect(wb_fixed)
        assert len(findings_after) == 0
    finally:
        if tmp_in_path.exists():
            tmp_in_path.unlink()
        if tmp_out_path.exists():
            tmp_out_path.unlink()


def test_r10_detects_dates_stored_as_text():
    wb = read_workbook(R10_FIXTURE_PATH)
    r10 = RuleR10()

    findings = r10.detect(wb)
    refs = {f.ref for f in findings}
    assert refs == {"B2", "C2", "D2", "B3", "C3", "D3"}
    assert all(f.rule_id == "R10" for f in findings)
    assert all(f.risk == "value" for f in findings)
    assert all(f.severity == "warning" for f in findings)

    findings_map = {f.ref: f for f in findings}

    edits_b2 = r10.fix(wb, findings_map["B2"])
    assert len(edits_b2) == 2
    assert edits_b2[0].op == "SetValue"
    assert edits_b2[0].value == 45306  # 2024-01-15
    assert edits_b2[0].cell_type is None
    assert edits_b2[1].op == "SetNumFmt"
    assert edits_b2[1].num_fmt_code == "dd/mm/yyyy"

    edits_c2 = r10.fix(wb, findings_map["C2"])
    assert edits_c2[0].value == 45306

    edits_d2 = r10.fix(wb, findings_map["D2"])
    assert edits_d2[0].value == 45306

    edits_b3 = r10.fix(wb, findings_map["B3"])
    assert edits_b3[0].value == 45047  # 2023-05-01

    edits_c3 = r10.fix(wb, findings_map["C3"])
    assert edits_c3[0].value == 44926  # 2022-12-31

    edits_d3 = r10.fix(wb, findings_map["D3"])
    assert edits_d3[0].value == 45351  # 2024-02-29


def test_r10_apply_fix_and_redetect():
    with (
        tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_in,
        tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_out,
    ):
        tmp_in_path = Path(tmp_in.name)
        tmp_out_path = Path(tmp_out.name)
    try:
        shutil.copy(R10_FIXTURE_PATH, tmp_in_path)
        wb = read_workbook(tmp_in_path)
        r10 = RuleR10()
        findings = r10.detect(wb)
        assert len(findings) == 6

        all_edits = []
        for f in findings:
            all_edits.extend(r10.fix(wb, f))

        apply_edits(tmp_in_path, tmp_out_path, all_edits)

        wb_fixed = read_workbook(tmp_out_path)
        findings_after = r10.detect(wb_fixed)
        assert len(findings_after) == 0
    finally:
        if tmp_in_path.exists():
            tmp_in_path.unlink()
        if tmp_out_path.exists():
            tmp_out_path.unlink()


def test_r12_detects_boolean_and_percentage_stored_as_text():
    wb = read_workbook(R12_FIXTURE_PATH)
    r12 = RuleR12()

    findings = r12.detect(wb)
    refs = {f.ref for f in findings}
    assert refs == {"B2", "C2", "D2", "B3", "C3", "D3", "B4", "C4", "D4"}
    assert all(f.rule_id == "R12" for f in findings)
    assert all(f.risk == "value" for f in findings)
    assert all(f.severity == "warning" for f in findings)

    findings_map = {f.ref: f for f in findings}

    # B2: "TRUE"
    edits_b2 = r12.fix(wb, findings_map["B2"])
    assert len(edits_b2) == 1
    assert edits_b2[0].op == "SetValue"
    assert edits_b2[0].value == 1
    assert edits_b2[0].cell_type == "b"

    # B3: "FALSE"
    edits_b3 = r12.fix(wb, findings_map["B3"])
    assert len(edits_b3) == 1
    assert edits_b3[0].op == "SetValue"
    assert edits_b3[0].value == 0
    assert edits_b3[0].cell_type == "b"

    # B4: "true"
    edits_b4 = r12.fix(wb, findings_map["B4"])
    assert len(edits_b4) == 1
    assert edits_b4[0].op == "SetValue"
    assert edits_b4[0].value == 1
    assert edits_b4[0].cell_type == "b"

    # C2: "12%" -> 0.12, num_fmt "0%"
    edits_c2 = r12.fix(wb, findings_map["C2"])
    assert len(edits_c2) == 2
    assert edits_c2[0].op == "SetValue"
    assert edits_c2[0].value == 0.12
    assert edits_c2[0].cell_type is None
    assert edits_c2[1].op == "SetNumFmt"
    assert edits_c2[1].num_fmt_code == "0%"

    # D2: "12.5%" -> 0.125, num_fmt "0.0%"
    edits_d2 = r12.fix(wb, findings_map["D2"])
    assert len(edits_d2) == 2
    assert edits_d2[0].value == 0.125
    assert edits_d2[1].num_fmt_code == "0.0%"

    # C3: "12,5%" -> 0.125, num_fmt "0.0%"
    edits_c3 = r12.fix(wb, findings_map["C3"])
    assert len(edits_c3) == 2
    assert edits_c3[0].value == 0.125
    assert edits_c3[1].num_fmt_code == "0.0%"

    # D3: "-5%" -> -0.05, num_fmt "0%"
    edits_d3 = r12.fix(wb, findings_map["D3"])
    assert len(edits_d3) == 2
    assert edits_d3[0].value == -0.05
    assert edits_d3[1].num_fmt_code == "0%"

    # C4: "100%" -> 1.0, num_fmt "0%"
    edits_c4 = r12.fix(wb, findings_map["C4"])
    assert len(edits_c4) == 2
    assert edits_c4[0].value == 1.0
    assert edits_c4[1].num_fmt_code == "0%"

    # D4: "0.5%" -> 0.005, num_fmt "0.0%"
    edits_d4 = r12.fix(wb, findings_map["D4"])
    assert len(edits_d4) == 2
    assert edits_d4[0].value == 0.005
    assert edits_d4[1].num_fmt_code == "0.0%"


def test_r12_apply_fix_and_redetect():
    with (
        tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_in,
        tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_out,
    ):
        tmp_in_path = Path(tmp_in.name)
        tmp_out_path = Path(tmp_out.name)
    try:
        shutil.copy(R12_FIXTURE_PATH, tmp_in_path)
        wb = read_workbook(tmp_in_path)
        r12 = RuleR12()
        findings = r12.detect(wb)
        assert len(findings) == 9

        all_edits = []
        for f in findings:
            all_edits.extend(r12.fix(wb, f))

        apply_edits(tmp_in_path, tmp_out_path, all_edits)

        wb_fixed = read_workbook(tmp_out_path)
        findings_after = r12.detect(wb_fixed)
        assert len(findings_after) == 0
    finally:
        if tmp_in_path.exists():
            tmp_in_path.unlink()
        if tmp_out_path.exists():
            tmp_out_path.unlink()


def test_r13_detects_percentage_stored_at_wrong_scale():
    wb = read_workbook(R13_FIXTURE_PATH)
    r13 = RuleR13()

    findings = r13.detect(wb)
    refs = {f.ref for f in findings}
    assert refs == {"B8", "B9", "C10", "C11", "B12", "C13"}
    assert len(findings) == 6
    assert all(f.rule_id == "R13" for f in findings)
    assert all(f.risk == "value" for f in findings)
    assert all(f.severity == "warning" for f in findings)
    assert r13.auto_fixable is False

    # Test fix returns empty list or raises (report only)
    assert r13.fix(wb, findings[0]) == []

