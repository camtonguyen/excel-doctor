import time
import zipfile
from pathlib import Path

from backend.audit.base import registry
from backend.workbook.reader import read_workbook


def test_200k_cells_scan_under_20_seconds(tmp_path: Path):
    """Milestone 9: 200k-cell file scans in under 20 seconds (§8 Milestone 9, §7 huge.xlsx, §9 Trap 16)."""
    xlsx_path = tmp_path / "huge_200k.xlsx"

    # Generate synthetic 200k cells (20 columns x 10,000 rows)
    # Mixed with plain numbers, strings, and formulas
    cols = [
        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
        "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
    ]
    with zipfile.ZipFile(xlsx_path, "w") as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>",
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Sheet1" r:id="rId1"/></sheets>'
            "</workbook>",
        )

        sheet_parts = [
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                "<sheetData>"
            )
        ]
        for r in range(1, 10001):
            row_cells = []
            for c in cols:
                # Add some formulas to column T
                if c == "T":
                    row_cells.append(f'<c r="{c}{r}"><f>SUM(A{r}:S{r})</f><v>{r * 19}</v></c>')
                else:
                    row_cells.append(f'<c r="{c}{r}"><v>{r}</v></c>')
            sheet_parts.append(f'<row r="{r}">{"".join(row_cells)}</row>')
        sheet_parts.append("</sheetData></worksheet>")

        z.writestr("xl/worksheets/sheet1.xml", "\n".join(sheet_parts))

    # Benchmark read + full rule suite detect
    t_start = time.perf_counter()
    wb = read_workbook(xlsx_path)
    total_cells = sum(len(s.cells) for s in wb.sheets.values())
    assert total_cells == 200000

    rules = registry.get_all()
    assert len(rules) >= 23

    all_findings = []
    for rule in rules:
        all_findings.extend(rule.detect(wb))

    elapsed = time.perf_counter() - t_start
    # Assert performance threshold: under 20 seconds
    assert elapsed < 20.0, f"Scan took {elapsed:.2f}s, exceeding 20s requirement"
