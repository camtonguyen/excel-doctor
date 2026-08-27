from pathlib import Path

from backend.workbook.reader import read_workbook

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures"


def test_iter_cells_visits_every_cell_once():
    wb = read_workbook(FIXTURES_DIR / "sokho_google.xlsx")

    visited = list(wb.iter_cells())
    expected_total = sum(len(sheet.cells) for sheet in wb.sheets.values())

    assert len(visited) == expected_total
    assert {(sheet_name, ref) for sheet_name, ref, _ in visited} == {
        (sheet_name, ref)
        for sheet_name, sheet in wb.sheets.items()
        for ref in sheet.cells
    }
