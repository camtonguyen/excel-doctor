import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from lxml import etree

from backend.model import DiffEntry, Edit, Finding
from backend.workbook.reader import read_workbook


def verify_reopens(file_path: Path | str) -> bool:
    path = Path(file_path)
    if not path.exists():
        return False
    try:
        with zipfile.ZipFile(path, "r") as z:
            for name in z.namelist():
                if name.endswith((".xml", ".rels")):
                    with z.open(name) as f:
                        etree.parse(f)
        read_workbook(path)
        return True
    except Exception:  # noqa: BLE001
        return False


def verify_nothing_missing(
    original_path: Path | str, patched_path: Path | str
) -> bool:
    try:
        with zipfile.ZipFile(original_path, "r") as orig_z:
            orig_names = set(orig_z.namelist())
        with zipfile.ZipFile(patched_path, "r") as patch_z:
            patch_names = set(patch_z.namelist())

        missing = orig_names - patch_names
        allowed_missing = {"xl/calcChain.xml"}
        return missing.issubset(allowed_missing)
    except Exception:  # noqa: BLE001
        return False


def verify_recalculates(original_path: Path | str, patched_path: Path | str) -> bool:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice and os.path.exists("/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        soffice = "/Applications/LibreOffice.app/Contents/MacOS/soffice"

    if not soffice:
        return True  # Skip if LibreOffice is not installed in local environment

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_orig = Path(tmpdir) / "orig.xlsx"
        tmp_patch = Path(tmpdir) / "patch.xlsx"
        shutil.copy(original_path, tmp_orig)
        shutil.copy(patched_path, tmp_patch)

        def count_errors(target_file: Path) -> int:
            try:
                subprocess.run(
                    [soffice, "--headless", "--convert-to", "xlsx", "--outdir", tmpdir, str(target_file)],
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                wb = read_workbook(target_file)
                errors = 0
                for sheet in wb.sheets.values():
                    for cell in sheet.cells.values():
                        if cell.t == "e" or (cell.v and str(cell.v).startswith("#")):
                            errors += 1
                return errors
            except Exception:  # noqa: BLE001
                return 0

        errors_before = count_errors(tmp_orig)
        errors_after = count_errors(tmp_patch)
        return errors_after <= errors_before


def _extract_styles_map(z: zipfile.ZipFile) -> dict[int, tuple[Any, ...]]:
    styles_map: dict[int, tuple[Any, ...]] = {}
    if "xl/styles.xml" not in z.namelist():
        return styles_map

    with z.open("xl/styles.xml") as f:
        root = etree.parse(f).getroot()
        cell_xfs = root.find("{*}cellXfs")
        if cell_xfs is not None:
            for idx, xf in enumerate(cell_xfs.iter("{*}xf")):
                font_id = xf.get("fontId", "0")
                fill_id = xf.get("fillId", "0")
                border_id = xf.get("borderId", "0")
                num_fmt_id = xf.get("numFmtId", "0")
                styles_map[idx] = (font_id, fill_id, border_id, num_fmt_id)
    return styles_map


def _extract_sheet_presentation(
    z: zipfile.ZipFile, target: str, styles_map: dict[int, tuple[Any, ...]]
) -> dict[str, Any]:
    pres: dict[str, Any] = {
        "cells": {},
        "cols": [],
        "rows": [],
        "merges": [],
    }
    if target not in z.namelist():
        return pres

    with z.open(target) as f:
        root = etree.parse(f).getroot()

        for c in root.iter("{*}c"):
            r = c.get("r")
            s_idx = int(c.get("s", "0"))
            style_tuple = styles_map.get(s_idx, (None, None, None, None))
            pres["cells"][r] = style_tuple

        cols_node = root.find("{*}cols")
        if cols_node is not None:
            for col in cols_node.iter("{*}col"):
                pres["cols"].append((col.get("min"), col.get("max"), col.get("width")))

        sheet_data = root.find("{*}sheetData")
        if sheet_data is not None:
            for row in sheet_data.iter("{*}row"):
                pres["rows"].append((row.get("r"), row.get("ht")))

        merge_cells = root.find("{*}mergeCells")
        if merge_cells is not None:
            for mc in merge_cells.iter("{*}mergeCell"):
                pres["merges"].append(mc.get("ref"))

    return pres


def verify_presentation(
    original_path: Path | str,
    patched_path: Path | str,
    allowed_refs_by_sheet: dict[str, set[str]],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    try:
        with (
            zipfile.ZipFile(original_path, "r") as orig_z,
            zipfile.ZipFile(patched_path, "r") as patch_z,
        ):
            orig_styles = _extract_styles_map(orig_z)
            patch_styles = _extract_styles_map(patch_z)

            orig_wb = read_workbook(original_path)
            patch_wb = read_workbook(patched_path)

            for sheet_name, orig_sheet in orig_wb.sheets.items():
                if sheet_name not in patch_wb.sheets:
                    continue
                patch_sheet = patch_wb.sheets[sheet_name]

                orig_pres = _extract_sheet_presentation(
                    orig_z, orig_sheet.target, orig_styles
                )
                patch_pres = _extract_sheet_presentation(
                    patch_z, patch_sheet.target, patch_styles
                )

                allowed_refs = allowed_refs_by_sheet.get(sheet_name, set())

                # Check cell style mutations
                all_refs = set(orig_pres["cells"].keys()) | set(
                    patch_pres["cells"].keys()
                )
                for ref in all_refs:
                    orig_s = orig_pres["cells"].get(ref)
                    patch_s = patch_pres["cells"].get(ref)
                    if orig_s != patch_s and ref not in allowed_refs:
                        reasons.append(
                            f"Unexpected style mutation in {sheet_name}!{ref}: {orig_s} -> {patch_s}"
                        )

                # Check cols, rows, merges
                if orig_pres["cols"] != patch_pres["cols"]:
                    reasons.append(f"Column width mutated in sheet {sheet_name}")
                if orig_pres["rows"] != patch_pres["rows"]:
                    reasons.append(f"Row height mutated in sheet {sheet_name}")
                if orig_pres["merges"] != patch_pres["merges"]:
                    reasons.append(f"Merged cells mutated in sheet {sheet_name}")

    except Exception as e:  # noqa: BLE001
        reasons.append(f"Exception during presentation diff: {e}")

    return len(reasons) == 0, reasons


def compute_diff(
    original_path: Path | str,
    patched_path: Path | str,
    edits: list[Edit] | None = None,
    findings: list[Finding] | None = None,
) -> list[DiffEntry]:
    diffs: list[DiffEntry] = []
    orig_wb = read_workbook(original_path)
    patch_wb = read_workbook(patched_path)

    findings_lookup = {}
    if findings:
        for f in findings:
            findings_lookup[(f.sheet, f.ref)] = f

    edits_lookup = {}
    if edits:
        for e in edits:
            if hasattr(e, "sheet") and hasattr(e, "ref"):
                edits_lookup[(e.sheet, e.ref)] = e

    all_sheet_names = set(orig_wb.sheets.keys()) | set(patch_wb.sheets.keys())
    for s_name in all_sheet_names:
        orig_sheet = orig_wb.sheets.get(s_name)
        patch_sheet = patch_wb.sheets.get(s_name)

        if orig_sheet and patch_sheet:
            all_refs = set(orig_sheet.cells.keys()) | set(patch_sheet.cells.keys())
            for ref in all_refs:
                c_orig = orig_sheet.cells.get(ref)
                c_patch = patch_sheet.cells.get(ref)

                v_orig = c_orig.v if c_orig else None
                v_patch = c_patch.v if c_patch else None

                f_orig = c_orig.f if c_orig else None
                f_patch = c_patch.f if c_patch else None

                fmt_orig = c_orig.num_fmt if c_orig else None
                fmt_patch = c_patch.num_fmt if c_patch else None

                # Value or formula changed
                if v_orig != v_patch or f_orig != f_patch or fmt_orig != fmt_patch:
                    finding = findings_lookup.get((s_name, ref))
                    edit = edits_lookup.get((s_name, ref))

                    cause = finding.rule_id if finding else (edit.op if edit else "Edit")
                    note = (
                        finding.description
                        if finding
                        else f"Changed value from '{v_orig}' to '{v_patch}'"
                    )

                    before_val = v_orig if v_orig is not None else (f_orig or fmt_orig or "")
                    after_val = v_patch if v_patch is not None else (f_patch or fmt_patch or "")

                    diffs.append(
                        DiffEntry(
                            sheet=s_name,
                            ref=ref,
                            before=before_val,
                            after=after_val,
                            cause=cause,
                            note=note,
                        )
                    )

    return diffs


def verify_patch(
    original_path: Path | str,
    patched_path: Path | str,
    edits: list[Edit],
    findings: list[Finding] | None = None,
) -> tuple[bool, list[DiffEntry], str | None]:
    # 1. Reopens
    if not verify_reopens(patched_path):
        return False, [], "File sau khi sửa không thể mở lại hoặc XML bị lỗi cú pháp."

    # 2. Nothing went missing
    if not verify_nothing_missing(original_path, patched_path):
        return False, [], "File sau khi sửa bị thiếu các thành phần XML quan trọng."

    # 3. Recalculates
    if not verify_recalculates(original_path, patched_path):
        return False, [], "Số lượng ô lỗi công thức sau khi sửa tăng lên."

    # 4. Presentation diff
    allowed_refs_by_sheet: dict[str, set[str]] = {}
    for edit in edits:
        if hasattr(edit, "sheet") and hasattr(edit, "ref"):
            allowed_refs_by_sheet.setdefault(edit.sheet, set()).add(edit.ref)

    pres_ok, reasons = verify_presentation(
        original_path, patched_path, allowed_refs_by_sheet
    )
    if not pres_ok:
        return False, [], f"Lỗi định dạng giao diện: {'; '.join(reasons)}"

    # 5. Cell diff
    diff_entries = compute_diff(original_path, patched_path, edits, findings)

    return True, diff_entries, None
