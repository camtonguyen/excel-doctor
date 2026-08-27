import zipfile
from pathlib import Path


def create_mock_xlsx(filename: str, contents: list[str]):
    """Creates a zip file (mock xlsx) containing empty files at the specified paths."""
    out_dir = Path(__file__).parent.parent.parent / "fixtures"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / filename
    
    with zipfile.ZipFile(out_path, "w") as z:
        for path in contents:
            z.writestr(path, b"")
    print(f"Created mock fixture: {out_path}")

if __name__ == "__main__":
    create_mock_xlsx("chart_pivot.xlsx", [
        "[Content_Types].xml",
        "xl/workbook.xml",
        "xl/charts/chart1.xml",
        "xl/pivotTables/pivotTable1.xml",
        "xl/pivotCache/pivotCacheDefinition1.xml"
    ])
    
    create_mock_xlsx("macro.xlsm", [
        "[Content_Types].xml",
        "xl/workbook.xml",
        "xl/vbaProject.bin"
    ])
    
    create_mock_xlsx("simple.xlsx", [
        "[Content_Types].xml",
        "xl/workbook.xml",
        "xl/worksheets/sheet1.xml"
    ])
