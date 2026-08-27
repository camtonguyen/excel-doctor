import zipfile
from pathlib import Path

from lxml import etree

from backend.model import CellEdit, SheetEdit
from backend.workbook.xml_patcher import apply_edits


def test_apply_set_value_inline(tmp_path: Path):
    input_path = tmp_path / "in.xlsx"
    output_path = tmp_path / "out.xlsx"
    
    with zipfile.ZipFile(input_path, "w") as z:
        z.writestr("xl/_rels/workbook.xml.rels", b'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", b'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/worksheets/sheet1.xml", b'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c></row></sheetData></worksheet>')
        z.writestr("[Content_Types].xml", b'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>')

    edits = [
        CellEdit(op="SetValue", sheet="Sheet1", ref="A1", value="Clean Text", cell_type="inlineStr")
    ]
    
    apply_edits(input_path, output_path, edits)
    
    assert output_path.exists()
    
    with zipfile.ZipFile(output_path, "r") as z:
        assert "xl/worksheets/sheet1.xml" in z.namelist()
        with z.open("xl/worksheets/sheet1.xml") as f:
            tree = etree.parse(f)
            root = tree.getroot()
            nsmap = root.nsmap
            ns = f"{{{nsmap.get(None)}}}"
            
            c = root.find(f".//{ns}c[@r='A1']")
            assert c is not None
            assert c.get("t") == "inlineStr"
            assert c.find(f"{ns}v") is None
            
            is_t = c.find(f"{ns}is/{ns}t")
            assert is_t is not None
            assert is_t.text == "Clean Text"


def test_apply_set_formula_drops_calc_chain(tmp_path: Path):
    input_path = tmp_path / "in.xlsx"
    output_path = tmp_path / "out.xlsx"
    
    with zipfile.ZipFile(input_path, "w") as z:
        z.writestr("xl/_rels/workbook.xml.rels", b'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/calcChain" Target="calcChain.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", b'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/worksheets/sheet1.xml", b'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="B2"><f>A1+1</f><v>2</v></c></row></sheetData></worksheet>')
        z.writestr("xl/calcChain.xml", b'<calcChain></calcChain>')
        z.writestr("[Content_Types].xml", b'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/xl/calcChain.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.calcChain+xml"/></Types>')

    edits = [
        CellEdit(op="SetFormula", sheet="Sheet1", ref="B2", formula="A1+100")
    ]
    
    apply_edits(input_path, output_path, edits)
    
    with zipfile.ZipFile(output_path, "r") as z:
        assert "xl/calcChain.xml" not in z.namelist()
        
        with z.open("xl/worksheets/sheet1.xml") as f:
            tree = etree.parse(f)
            root = tree.getroot()
            nsmap = root.nsmap
            ns = f"{{{nsmap.get(None)}}}"
            
            c = root.find(f".//{ns}c[@r='B2']")
            assert c is not None
            assert c.find(f"{ns}v") is None  # <v> must be dropped
            f_node = c.find(f"{ns}f")
            assert f_node is not None
            assert f_node.text == "A1+100"
            
        with z.open("[Content_Types].xml") as f:
            ct = f.read().decode("utf-8")
            assert "calcChain.xml" not in ct
            
        with z.open("xl/_rels/workbook.xml.rels") as f:
            rels = f.read().decode("utf-8")
            assert "calcChain.xml" not in rels
            
        with z.open("xl/workbook.xml") as f:
            tree = etree.parse(f)
            root = tree.getroot()
            nsmap = root.nsmap
            ns = f"{{{nsmap.get(None)}}}"
            calc_pr = root.find(f"{ns}calcPr")
            assert calc_pr is not None
            assert calc_pr.get("fullCalcOnLoad") == "1"


def test_apply_set_value_normal(tmp_path: Path):
    input_path = tmp_path / "in.xlsx"
    output_path = tmp_path / "out.xlsx"
    
    with zipfile.ZipFile(input_path, "w") as z:
        z.writestr("xl/_rels/workbook.xml.rels", b'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", b'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/worksheets/sheet1.xml", b'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="C3" t="s"><v>5</v></c></row></sheetData></worksheet>')

    edits = [
        CellEdit(op="SetValue", sheet="Sheet1", ref="C3", value="123.45")
    ]
    
    apply_edits(input_path, output_path, edits)
    
    with zipfile.ZipFile(output_path, "r") as z, z.open("xl/worksheets/sheet1.xml") as f:
        tree = etree.parse(f)
        root = tree.getroot()
        nsmap = root.nsmap
        ns = f"{{{nsmap.get(None)}}}"

        c = root.find(f".//{ns}c[@r='C3']")
        assert c is not None
        assert "t" not in c.attrib  # t is removed because no cell_type is provided

        v = c.find(f"{ns}v")
        assert v is not None
        assert v.text == "123.45"


def test_apply_rename_sheet(tmp_path: Path):
    input_path = tmp_path / "in.xlsx"
    output_path = tmp_path / "out.xlsx"
    
    with zipfile.ZipFile(input_path, "w") as z:
        z.writestr("xl/_rels/workbook.xml.rels", b'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", b'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Old[Name]" r:id="rId1"/><sheet name="OtherSheet" r:id="rId2"/></sheets><definedNames><definedName name="test_range">\'Old[Name]\'!A1:B2</definedName></definedNames></workbook>')
        z.writestr("xl/worksheets/sheet1.xml", b'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1"><f>\'Old[Name]\'!A2</f></c></row></sheetData></worksheet>')
        z.writestr("xl/worksheets/sheet2.xml", b'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1"><f>\'Old[Name]\'!A1 + OtherSheet!B1</f></c></row></sheetData></worksheet>')

    edits = [
        SheetEdit(op="RenameSheet", sheet="Old[Name]", new_name="Old_Name_")
    ]
    
    apply_edits(input_path, output_path, edits)
    
    with zipfile.ZipFile(output_path, "r") as z:
        with z.open("xl/workbook.xml") as f:
            tree = etree.parse(f)
            root = tree.getroot()
            nsmap = root.nsmap
            ns = f"{{{nsmap.get(None)}}}"
            
            # Check sheet name
            sheets = root.find(f"{ns}sheets")
            assert sheets is not None
            sheet_nodes = sheets.findall(f"{ns}sheet")
            assert len(sheet_nodes) == 2
            assert sheet_nodes[0].get("name") == "Old_Name_"
            assert sheet_nodes[1].get("name") == "OtherSheet"
            
            # Check defined name
            dns = root.find(f"{ns}definedNames")
            assert dns is not None
            dn = dns.find(f"{ns}definedName")
            assert dn is not None
            assert dn.text == "Old_Name_!A1:B2"
            
        with z.open("xl/worksheets/sheet1.xml") as f:
            tree = etree.parse(f)
            root = tree.getroot()
            nsmap = root.nsmap
            ns = f"{{{nsmap.get(None)}}}"
            
            c = root.find(f".//{ns}c[@r='A1']")
            f_node = c.find(f"{ns}f")
            assert f_node.text == "Old_Name_!A2"

        with z.open("xl/worksheets/sheet2.xml") as f:
            tree = etree.parse(f)
            root = tree.getroot()
            nsmap = root.nsmap
            ns = f"{{{nsmap.get(None)}}}"
            
            c = root.find(f".//{ns}c[@r='A1']")
            f_node = c.find(f"{ns}f")
            assert f_node.text == "Old_Name_!A1 + OtherSheet!B1"


def test_apply_clear_cell_plain_value_keeps_calc_chain(tmp_path: Path):
    input_path = tmp_path / "in.xlsx"
    output_path = tmp_path / "out.xlsx"

    with zipfile.ZipFile(input_path, "w") as z:
        z.writestr("xl/_rels/workbook.xml.rels", b'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/calcChain" Target="calcChain.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", b'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/worksheets/sheet1.xml", b'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="D4" s="3"><v>42</v></c></row></sheetData></worksheet>')
        z.writestr("xl/calcChain.xml", b'<calcChain></calcChain>')
        z.writestr("[Content_Types].xml", b'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/xl/calcChain.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.calcChain+xml"/></Types>')

    edits = [
        CellEdit(op="ClearCell", sheet="Sheet1", ref="D4")
    ]

    apply_edits(input_path, output_path, edits)

    with zipfile.ZipFile(output_path, "r") as z:
        assert "xl/calcChain.xml" in z.namelist()  # no formula touched, calcChain must survive

        with z.open("xl/worksheets/sheet1.xml") as f:
            tree = etree.parse(f)
            root = tree.getroot()
            ns = f"{{{root.nsmap.get(None)}}}"

            c = root.find(f".//{ns}c[@r='D4']")
            assert c is not None
            assert c.get("s") == "3"  # style untouched
            assert c.find(f"{ns}v") is None


def test_apply_clear_cell_with_formula_drops_calc_chain(tmp_path: Path):
    input_path = tmp_path / "in.xlsx"
    output_path = tmp_path / "out.xlsx"

    with zipfile.ZipFile(input_path, "w") as z:
        z.writestr("xl/_rels/workbook.xml.rels", b'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/calcChain" Target="calcChain.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", b'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/worksheets/sheet1.xml", b'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="E5"><f>A1+1</f><v>2</v></c></row></sheetData></worksheet>')
        z.writestr("xl/calcChain.xml", b'<calcChain></calcChain>')
        z.writestr("[Content_Types].xml", b'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/xl/calcChain.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.calcChain+xml"/></Types>')

    edits = [
        CellEdit(op="ClearCell", sheet="Sheet1", ref="E5")
    ]

    apply_edits(input_path, output_path, edits)

    with zipfile.ZipFile(output_path, "r") as z:
        assert "xl/calcChain.xml" not in z.namelist()  # clearing a formula cell drops the chain

        with z.open("xl/worksheets/sheet1.xml") as f:
            tree = etree.parse(f)
            root = tree.getroot()
            ns = f"{{{root.nsmap.get(None)}}}"

            c = root.find(f".//{ns}c[@r='E5']")
            assert c is not None
            assert c.find(f"{ns}v") is None
            assert c.find(f"{ns}f") is None
