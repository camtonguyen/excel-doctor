import zipfile
from collections import defaultdict
from pathlib import Path

from lxml import etree

from backend.model import CellEdit, Edit, SheetEdit
from backend.workbook.formula import rename_sheet_in_formula

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

def _any_formula_changed(zin: zipfile.ZipFile, sheet_targets: dict[str, str], cell_edits_by_sheet: dict, rename_map: dict) -> bool:
    """True only if some edit actually changes a cell's <f> — not just any ClearCell/SetFormula op."""
    # Renaming a sheet changes formulas across ALL sheets if they reference it, 
    # but technically we only drop calcChain if we *modify* a formula's logic or a cell's formula.
    # Actually, if we update a sheet reference, Excel will recalculate it. Let's just drop calcChain if rename_map is not empty.
    if rename_map:
        return True

    for sheet_name, sheet_edits in cell_edits_by_sheet.items():
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

def apply_edits(input_path: str | Path, output_path: str | Path, edits: list[Edit]) -> None:
    cell_edits_by_sheet = defaultdict(list)
    rename_map = {}
    
    for edit in edits:
        if isinstance(edit, CellEdit):
            cell_edits_by_sheet[edit.sheet].append(edit)
        elif isinstance(edit, SheetEdit) and edit.op == "RenameSheet":
            rename_map[edit.sheet] = edit.new_name

    with zipfile.ZipFile(input_path, "r") as zin:
        sheet_targets = get_sheet_targets(zin)
        calc_chain_dropped = _any_formula_changed(zin, sheet_targets, cell_edits_by_sheet, rename_map)

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

                # If this item is a sheet XML, we must check if we need to apply CellEdits OR RenameMap (update references)
                sheet_name = next((name for name, target in sheet_targets.items() if target == item.filename), None)
                if sheet_name is not None:
                    has_cell_edits = sheet_name in cell_edits_by_sheet
                    has_renames = len(rename_map) > 0
                    
                    if has_cell_edits or has_renames:
                        sheet_edits = cell_edits_by_sheet.get(sheet_name, [])
                        
                        def mutate_sheet(root, ns, sheet_edits=sheet_edits, rename_map=rename_map, has_renames=has_renames):
                            for c_node in root.iter(f"{ns}c"):
                                ref = c_node.get("r")
                                
                                # First, apply formula updates due to renames
                                if has_renames:
                                    f_node = c_node.find(f"{ns}f")
                                    if f_node is not None and f_node.text:
                                        new_f = f_node.text
                                        for old_name, new_name in rename_map.items():
                                            new_f = rename_sheet_in_formula(new_f, old_name, new_name)
                                        f_node.text = new_f

                                # Then apply specific CellEdits (which might overwrite the formula anyway)
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
                    def mutate_workbook(root, ns, rename_map=rename_map):
                        calc_pr = root.find(f"{ns}calcPr")
                        if calc_pr is None:
                            calc_pr = etree.SubElement(root, f"{ns}calcPr")
                        calc_pr.set("fullCalcOnLoad", "1")
                        
                        # Apply renames to <sheet> elements
                        if rename_map:
                            sheets_node = root.find(f"{ns}sheets")
                            if sheets_node is not None:
                                for sheet_node in sheets_node.iter(f"{ns}sheet"):
                                    name = sheet_node.get("name")
                                    if name in rename_map:
                                        sheet_node.set("name", rename_map[name])
                                        
                            # Apply renames to <definedName> elements
                            defined_names = root.find(f"{ns}definedNames")
                            if defined_names is not None:
                                for dn in defined_names.iter(f"{ns}definedName"):
                                    if dn.text:
                                        new_text = dn.text
                                        for old_name, new_name in rename_map.items():
                                            new_text = rename_sheet_in_formula(new_text, old_name, new_name)
                                        dn.text = new_text

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
