import shutil
import tempfile
import zipfile
from pathlib import Path

from backend.audit.rules_datatype import RuleR14
from backend.audit.rules_display import RuleR11
from backend.verify.verifier import (
    verify_nothing_missing,
    verify_patch,
    verify_presentation,
    verify_reopens,
)
from backend.workbook.reader import read_workbook
from backend.workbook.xml_patcher import apply_edits

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures"
R11_FIXTURE_PATH = FIXTURES_DIR / "r11_date_serial.xlsx"
WHITESPACE_FIXTURE_PATH = FIXTURES_DIR / "whitespace.xlsx"


def test_verify_reopens_valid_and_invalid_files():
    assert verify_reopens(R11_FIXTURE_PATH) is True

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        # Write corrupted zip
        with zipfile.ZipFile(tmp_path, "w") as z:
            z.writestr("xl/worksheets/sheet1.xml", "<corrupted xml unclosed tag")
        assert verify_reopens(tmp_path) is False
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def test_verify_nothing_missing():
    with (
        tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp1,
        tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp2,
    ):
        p1 = Path(tmp1.name)
        p2 = Path(tmp2.name)
    try:
        shutil.copy(R11_FIXTURE_PATH, p1)
        shutil.copy(R11_FIXTURE_PATH, p2)

        # Same files -> True
        assert verify_nothing_missing(p1, p2) is True

        # Drop a non-calcChain file from p2 -> False
        with (
            zipfile.ZipFile(p1, "r") as zin,
            zipfile.ZipFile(p2, "w") as zout,
        ):
            for item in zin.infolist():
                if item.filename != "xl/styles.xml":
                    zout.writestr(item, zin.read(item.filename))
        assert verify_nothing_missing(p1, p2) is False
    finally:
        if p1.exists():
            p1.unlink()
        if p2.exists():
            p2.unlink()


def test_presentation_diff_passes_on_allowed_edits():
    with (
        tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_in,
        tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_out,
    ):
        in_path = Path(tmp_in.name)
        out_path = Path(tmp_out.name)
    try:
        shutil.copy(R11_FIXTURE_PATH, in_path)
        wb = read_workbook(in_path)
        r11 = RuleR11()
        findings = r11.detect(wb)

        edits = []
        for f in findings:
            edits.extend(r11.fix(wb, f))

        apply_edits(in_path, out_path, edits)

        allowed_refs = {"Sheet1": {f.ref for f in findings}}
        ok, reasons = verify_presentation(in_path, out_path, allowed_refs)
        assert ok is True
        assert len(reasons) == 0

        # Disallow edits to test presentation failure
        ok_fail, reasons_fail = verify_presentation(in_path, out_path, {"Sheet1": set()})
        assert ok_fail is False
        assert len(reasons_fail) > 0
    finally:
        if in_path.exists():
            in_path.unlink()
        if out_path.exists():
            out_path.unlink()


def test_compute_diff_and_verify_patch_chain():
    with (
        tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_in,
        tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_out,
    ):
        in_path = Path(tmp_in.name)
        out_path = Path(tmp_out.name)
    try:
        shutil.copy(WHITESPACE_FIXTURE_PATH, in_path)
        wb = read_workbook(in_path)
        r14 = RuleR14()
        findings = r14.detect(wb)

        edits = []
        for f in findings:
            edits.extend(r14.fix(wb, f))

        apply_edits(in_path, out_path, edits)

        ok, diffs, err = verify_patch(in_path, out_path, edits, findings)
        assert ok is True
        assert err is None
        assert len(diffs) > 0
        assert all(d.cause == "R14" for d in diffs)
    finally:
        if in_path.exists():
            in_path.unlink()
        if out_path.exists():
            out_path.unlink()
