import zipfile
from collections import defaultdict
from pathlib import Path

from lxml import etree

from backend.model import CellEdit

SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
RELATIONSHIPS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

def _ns(root, default: str) -> str:
    return f"{{{root.nsmap.get(None, default)}}}"

def _clear_cell_children(c_node, ns: str) -> None:
    for tag in (f"{ns}v", f"{ns}f", f"{ns}is"):
        node = c_node.find(tag)
        if node is not None:
            c_node.remove(node)

def _rewrite_xml_part(zin: zipfile.ZipFile, zout: zipfile.ZipFile, item: zipfile.ZipInfo, default_ns: str, mutate) -> None:
    with zin.open(item) as f:
        tree = etree.parse(f)
    root = tree.getroot()
    mutate(root, _ns(root, default_ns))
    xml_bytes = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)
    zout.writestr(item, xml_bytes, compress_type=item.compress_type)

def get_sheet_targets(zin: zipfile.ZipFile) -> dict[str, str]:
    """Returns a dict mapping sheet names to their target XML paths inside the zip."""
    sheet_targets = {}
    rel_targets = {}

    if "xl/_rels/workbook.xml.rels" in zin.namelist():
        with zin.open("xl/_rels/workbook.xml.rels") as f:
            tree = etree.parse(f)
            for rel in tree.getroot().iter("{*}Relationship"):
                if "worksheet" in rel.get("Type", ""):
                    rel_targets[rel.get("Id")] = "xl/" + rel.get("Target")

    if "xl/workbook.xml" in zin.namelist():
        with zin.open("xl/workbook.xml") as f:
            tree = etree.parse(f)
            for sheet in tree.getroot().iter("{*}sheet"):
                name = sheet.get("name")
                r_id = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                target = rel_targets.get(r_id)
                if name and target:
                    sheet_targets[name] = target

    return sheet_targets

def _any_formula_changed(zin: zipfile.ZipFile, sheet_targets: dict[str, str], edits_by_sheet: dict) -> bool:
    """True only if some edit actually changes a cell's <f> — not just any ClearCell/SetFormula op."""
    for sheet_name, sheet_edits in edits_by_sheet.items():
        if any(e.op == "SetFormula" for e in sheet_edits):
            return True

        clear_refs = {e.ref for e in sheet_edits if e.op == "ClearCell"}
        target = sheet_targets.get(sheet_name)
        if not clear_refs or target not in zin.namelist():
            continue

        with zin.open(target) as f:
            root = etree.parse(f).getroot()
        ns = _ns(root, SPREADSHEET_NS)
        for c_node in root.iter(f"{ns}c"):
            if c_node.get("r") in clear_refs and c_node.find(f"{ns}f") is not None:
                return True

    return False

def apply_edits(input_path: str | Path, output_path: str | Path, edits: list[CellEdit]) -> None:
    edits_by_sheet = defaultdict(list)
    for edit in edits:
        edits_by_sheet[edit.sheet].append(edit)

    with zipfile.ZipFile(input_path, "r") as zin:
        sheet_targets = get_sheet_targets(zin)
        calc_chain_dropped = _any_formula_changed(zin, sheet_targets, edits_by_sheet)

        # ponytail: zip format doesn't record deflate level as metadata, so only
        # compress_type (STORED/DEFLATED) is recoverable per entry; level itself
        # can't be "preserved" from the source, only chosen consistently here.
        with zipfile.ZipFile(output_path, "w") as zout:
            for item in zin.infolist():
                if item.is_dir():
                    zout.writestr(item, b"")
                    continue

                if item.filename == "xl/calcChain.xml" and calc_chain_dropped:
                    continue

                sheet_name = next((name for name, target in sheet_targets.items() if target == item.filename), None)
                if sheet_name is not None and sheet_name in edits_by_sheet:
                    sheet_edits = edits_by_sheet[sheet_name]

                    def mutate_sheet(root, ns, sheet_edits=sheet_edits):
                        for c_node in root.iter(f"{ns}c"):
                            ref = c_node.get("r")
                            for edit in (e for e in sheet_edits if e.ref == ref):
                                if edit.op == "SetValue":
                                    if edit.cell_type:
                                        c_node.set("t", edit.cell_type)
                                    elif "t" in c_node.attrib:
                                        del c_node.attrib["t"]

                                    _clear_cell_children(c_node, ns)

                                    if edit.cell_type == "inlineStr":
                                        is_node = etree.SubElement(c_node, f"{ns}is")
                                        t_node = etree.SubElement(is_node, f"{ns}t")
                                        t_node.text = str(edit.value)
                                    else:
                                        v_node = etree.SubElement(c_node, f"{ns}v")
                                        v_node.text = str(edit.value)

                                elif edit.op == "SetFormula":
                                    _clear_cell_children(c_node, ns)
                                    f_node = etree.SubElement(c_node, f"{ns}f")
                                    f_node.text = str(edit.formula)

                                elif edit.op == "ClearCell":
                                    _clear_cell_children(c_node, ns)

                    _rewrite_xml_part(zin, zout, item, SPREADSHEET_NS, mutate_sheet)
                    continue

                if item.filename == "xl/workbook.xml":
                    def mutate_workbook(root, ns):
                        calc_pr = root.find(f"{ns}calcPr")
                        if calc_pr is None:
                            calc_pr = etree.SubElement(root, f"{ns}calcPr")
                        calc_pr.set("fullCalcOnLoad", "1")

                    _rewrite_xml_part(zin, zout, item, SPREADSHEET_NS, mutate_workbook)
                    continue

                if calc_chain_dropped and item.filename == "[Content_Types].xml":
                    def mutate_content_types(root, ns):
                        for override in root.iter(f"{ns}Override"):
                            if override.get("PartName") == "/xl/calcChain.xml":
                                override.getparent().remove(override)

                    _rewrite_xml_part(zin, zout, item, CONTENT_TYPES_NS, mutate_content_types)
                    continue

                if calc_chain_dropped and item.filename == "xl/_rels/workbook.xml.rels":
                    def mutate_rels(root, ns):
                        for rel in root.iter(f"{ns}Relationship"):
                            if rel.get("Target") in ("calcChain.xml", "/xl/calcChain.xml"):
                                rel.getparent().remove(rel)

                    _rewrite_xml_part(zin, zout, item, RELATIONSHIPS_NS, mutate_rels)
                    continue

                zout.writestr(item, zin.read(item.filename), compress_type=item.compress_type)
