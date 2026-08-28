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
    create_mock_xlsx(
        "chart_pivot.xlsx",
        [
            "[Content_Types].xml",
            "xl/workbook.xml",
            "xl/charts/chart1.xml",
            "xl/pivotTables/pivotTable1.xml",
            "xl/pivotCache/pivotCacheDefinition1.xml",
        ],
    )

    create_mock_xlsx(
        "macro.xlsm", ["[Content_Types].xml", "xl/workbook.xml", "xl/vbaProject.bin"]
    )

    create_mock_xlsx(
        "simple.xlsx",
        ["[Content_Types].xml", "xl/workbook.xml", "xl/worksheets/sheet1.xml"],
    )

    def create_sokho_google():
        out_dir = Path(__file__).parent.parent.parent / "fixtures"
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / "sokho_google.xlsx"

        with zipfile.ZipFile(out_path, "w") as z:
            z.writestr(
                "xl/sharedStrings.xml",
                b'<?xml version="1.0" encoding="UTF-8"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>#REF!</t></si><si><t>Just text</t></si></sst>',
            )

            z.writestr(
                "xl/_rels/workbook.xml.rels",
                b'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
            )

            z.writestr(
                "xl/workbook.xml",
                b'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" r:id="rId1"/></sheets></workbook>',
            )

            # R01: <f> contains #REF!
            # R02: t="e" (error value)
            # R03: t="s" and shared string == #REF! without <f>
            # R04: f="A1*2" where A1 evaluates to ""
            # R05: f="'Missing Sheet'!A1"

            sheet_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                <sheetData>
                    <row r="1">
                        <c r="A1" t="str"><v></v></c> <!-- empty string for R04 -->
                        <c r="B1"><f>A1*2</f><v>#VALUE!</v></c> <!-- R04 violation -->
                    </row>
                    <row r="2">
                        <c r="A2" t="e"><f>A1+#REF!</f><v>#REF!</v></c> <!-- R01 and R02 violation -->
                        <c r="B2" t="s"><v>0</v></c> <!-- R03 violation: 0 maps to '#REF!' in shared strings -->
                    </row>
                    <row r="3">
                        <c r="A3"><f>'Missing Sheet'!A1</f><v>#REF!</v></c> <!-- R05 violation -->
                    </row>
                </sheetData>
            </worksheet>
            """
            z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        print(f"Created complex fixture: {out_path}")

    create_sokho_google()

    def create_whitespace_fixture():
        out_dir = Path(__file__).parent.parent.parent / "fixtures"
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / "whitespace.xlsx"

        with zipfile.ZipFile(out_path, "w") as z:
            # si0: leading/trailing spaces
            # si1: doubled space
            # si2: NBSP ( )
            # si3: zero-width space (​)
            # si4: clean control, no defect
            shared_strings = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                '<si><t xml:space="preserve">  Doanh Thu  </t></si>'
                "<si><t>Doanh  Thu</t></si>"
                "<si><t>Doanh Thu</t></si>"
                "<si><t>Do\u200banh Thu</t></si>"
                "<si><t>Doanh Thu</t></si>"
                "</sst>"
            ).encode()
            z.writestr("xl/sharedStrings.xml", shared_strings)

            z.writestr(
                "xl/_rels/workbook.xml.rels",
                b'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
            )

            z.writestr(
                "xl/workbook.xml",
                b'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" r:id="rId1"/></sheets></workbook>',
            )

            sheet_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                <sheetData>
                    <row r="1">
                        <c r="A1" t="s"><v>0</v></c> <!-- leading/trailing spaces -->
                        <c r="A2" t="s"><v>1</v></c> <!-- doubled space -->
                        <c r="A3" t="s"><v>2</v></c> <!-- NBSP -->
                        <c r="A4" t="s"><v>3</v></c> <!-- zero-width space -->
                        <c r="A5" t="s"><v>4</v></c> <!-- clean, no defect -->
                    </row>
                </sheetData>
            </worksheet>
            """
            z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        print(f"Created whitespace fixture: {out_path}")

    create_whitespace_fixture()
