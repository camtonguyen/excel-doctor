import zipfile
from collections import defaultdict
from pathlib import Path

from lxml import etree

from backend.model import CellEdit

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

def apply_edits(input_path: str | Path, output_path: str | Path, edits: list[CellEdit]) -> None:
    edits_by_sheet = defaultdict(list)
    for edit in edits:
        edits_by_sheet[edit.sheet].append(edit)
        
    calc_chain_dropped = any(e.op in ("SetFormula", "ClearCell") for e in edits)
    
    with zipfile.ZipFile(input_path, "r") as zin:
        sheet_targets = get_sheet_targets(zin)
        
        with zipfile.ZipFile(output_path, "w") as zout:
            for item in zin.infolist():
                if item.is_dir():
                    continue
                
                # Drop calcChain if any formula was edited
                if item.filename == "xl/calcChain.xml":
                    if calc_chain_dropped:
                        continue
                
                is_sheet = False
                for sheet_name, sheet_edits in edits_by_sheet.items():
                    if sheet_targets.get(sheet_name) == item.filename:
                        is_sheet = True
                        with zin.open(item) as f:
                            tree = etree.parse(f)
                        root = tree.getroot()
                        
                        nsmap = root.nsmap
                        default_ns = nsmap.get(None, "http://schemas.openxmlformats.org/spreadsheetml/2006/main")
                        ns = f"{{{default_ns}}}"
                        
                        for c_node in root.iter(f"{ns}c"):
                            ref = c_node.get("r")
                            ref_edits = [e for e in sheet_edits if e.ref == ref]
                            for edit in ref_edits:
                                if edit.op == "SetValue":
                                    if edit.cell_type:
                                        c_node.set("t", edit.cell_type)
                                    else:
                                        if "t" in c_node.attrib:
                                            del c_node.attrib["t"]
                                            
                                    for tag in (f"{ns}v", f"{ns}f", f"{ns}is"):
                                        node = c_node.find(tag)
                                        if node is not None:
                                            c_node.remove(node)
                                            
                                    if edit.cell_type == "inlineStr":
                                        is_node = etree.SubElement(c_node, f"{ns}is")
                                        t_node = etree.SubElement(is_node, f"{ns}t")
                                        t_node.text = str(edit.value)
                                    else:
                                        v_node = etree.SubElement(c_node, f"{ns}v")
                                        v_node.text = str(edit.value)
                                        
                                elif edit.op == "SetFormula":
                                    for tag in (f"{ns}v", f"{ns}f", f"{ns}is"):
                                        node = c_node.find(tag)
                                        if node is not None:
                                            c_node.remove(node)
                                            
                                    f_node = etree.SubElement(c_node, f"{ns}f")
                                    f_node.text = str(edit.formula)
                                    
                                elif edit.op == "ClearCell":
                                    for tag in (f"{ns}v", f"{ns}f", f"{ns}is"):
                                        node = c_node.find(tag)
                                        if node is not None:
                                            c_node.remove(node)

                        xml_bytes = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)
                        zout.writestr(item, xml_bytes, compress_type=item.compress_type)
                        break
                        
                if is_sheet:
                    continue
                
                if item.filename == "xl/workbook.xml":
                    with zin.open(item) as f:
                        tree = etree.parse(f)
                    root = tree.getroot()
                    nsmap = root.nsmap
                    default_ns = nsmap.get(None, "http://schemas.openxmlformats.org/spreadsheetml/2006/main")
                    ns = f"{{{default_ns}}}"
                    calc_pr = root.find(f"{ns}calcPr")
                    if calc_pr is None:
                        calc_pr = etree.SubElement(root, f"{ns}calcPr")
                    calc_pr.set("fullCalcOnLoad", "1")
                    xml_bytes = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)
                    zout.writestr(item, xml_bytes, compress_type=item.compress_type)
                    continue

                if calc_chain_dropped:
                    if item.filename == "[Content_Types].xml":
                        with zin.open(item) as f:
                            tree = etree.parse(f)
                        root = tree.getroot()
                        nsmap = root.nsmap
                        default_ns = nsmap.get(None, "http://schemas.openxmlformats.org/package/2006/content-types")
                        ns = f"{{{default_ns}}}"
                        for override in root.iter(f"{ns}Override"):
                            if override.get("PartName") == "/xl/calcChain.xml":
                                override.getparent().remove(override)
                        xml_bytes = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)
                        zout.writestr(item, xml_bytes, compress_type=item.compress_type)
                        continue

                    if item.filename == "xl/_rels/workbook.xml.rels":
                        with zin.open(item) as f:
                            tree = etree.parse(f)
                        root = tree.getroot()
                        nsmap = root.nsmap
                        default_ns = nsmap.get(None, "http://schemas.openxmlformats.org/package/2006/relationships")
                        ns = f"{{{default_ns}}}"
                        for rel in root.iter(f"{ns}Relationship"):
                            if rel.get("Target") == "calcChain.xml" or rel.get("Target") == "/xl/calcChain.xml":
                                rel.getparent().remove(rel)
                        xml_bytes = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)
                        zout.writestr(item, xml_bytes, compress_type=item.compress_type)
                        continue

                zout.writestr(item, zin.read(item.filename), compress_type=item.compress_type)
