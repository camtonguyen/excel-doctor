from lxml import etree

from backend.workbook.styles import ensure_xf


def test_ensure_xf_creates_new_num_fmt_and_xf():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
        <numFmts count="1">
            <numFmt numFmtId="164" formatCode="yyyy-mm-dd"/>
        </numFmts>
        <cellXfs count="2">
            <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
            <xf numFmtId="164" fontId="1" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
        </cellXfs>
    </styleSheet>
    """
    root = etree.fromstring(xml)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

    # Use base_xf_index = 0 (the default one), and set format to "dd/mm/yyyy"
    new_index = ensure_xf(root, ns, 0, "dd/mm/yyyy")

    # Should have added a new numFmt and a new cellXf
    assert new_index == 2

    num_fmts = root.find(f"{ns}numFmts")
    assert num_fmts.get("count") == "2"
    assert len(num_fmts.findall(f"{ns}numFmt")) == 2
    new_fmt = num_fmts.findall(f"{ns}numFmt")[1]
    assert new_fmt.get("numFmtId") == "165"
    assert new_fmt.get("formatCode") == "dd/mm/yyyy"

    cell_xfs = root.find(f"{ns}cellXfs")
    assert cell_xfs.get("count") == "3"
    assert len(cell_xfs.findall(f"{ns}xf")) == 3
    new_xf = cell_xfs.findall(f"{ns}xf")[2]
    assert new_xf.get("numFmtId") == "165"
    assert new_xf.get("fontId") == "0"
    assert new_xf.get("applyNumberFormat") == "1"


def test_ensure_xf_deduplicates():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
        <numFmts count="1">
            <numFmt numFmtId="164" formatCode="dd/mm/yyyy"/>
        </numFmts>
        <cellXfs count="2">
            <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
            <xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
        </cellXfs>
    </styleSheet>
    """
    root = etree.fromstring(xml)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

    # Use base_xf_index = 0, format "dd/mm/yyyy"
    # This combination (fontId=0, numFmtId=164, applyNumberFormat=1) exactly matches index 1!
    new_index = ensure_xf(root, ns, 0, "dd/mm/yyyy")

    assert new_index == 1

    num_fmts = root.find(f"{ns}numFmts")
    assert num_fmts.get("count") == "1"

    cell_xfs = root.find(f"{ns}cellXfs")
    assert cell_xfs.get("count") == "2"


def test_ensure_xf_creates_num_fmts_if_missing():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
        <cellXfs count="1">
            <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
        </cellXfs>
    </styleSheet>
    """
    root = etree.fromstring(xml)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

    new_index = ensure_xf(root, ns, 0, "dd/mm/yyyy")
    assert new_index == 1

    num_fmts = root.find(f"{ns}numFmts")
    assert num_fmts is not None
    assert num_fmts.get("count") == "1"
    assert num_fmts.find(f"{ns}numFmt").get("numFmtId") == "164"
