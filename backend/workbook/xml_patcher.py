import zipfile
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from lxml import etree

from backend.model import CellEdit, Edit, SheetEdit, WorkbookEdit
from backend.workbook.formula import rename_sheet_in_formula
from backend.workbook.styles import ensure_xf

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


def _rewrite_xml_part(
    zin: zipfile.ZipFile,
    zout: zipfile.ZipFile,
    item: zipfile.ZipInfo,
    default_ns: str,
    mutate,
) -> None:
    with zin.open(item) as f:
        tree = etree.parse(f)
    root = tree.getroot()
    mutate(root, _ns(root, default_ns))
    xml_bytes = etree.tostring(
        tree, xml_declaration=True, encoding="UTF-8", standalone=True
    )
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
                    target_path = rel.get("Target", "")
                    if target_path.startswith("/"):
                        rel_targets[rel.get("Id")] = target_path.lstrip("/")
                    else:
                        rel_targets[rel.get("Id")] = "xl/" + target_path

    if "xl/workbook.xml" in zin.namelist():
        with zin.open("xl/workbook.xml") as f:
            tree = etree.parse(f)
            for sheet in tree.getroot().iter("{*}sheet"):
                name = sheet.get("name")
                r_id = sheet.get(
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                )
                target = rel_targets.get(r_id)
                if name and target:
                    sheet_targets[name] = target

    return sheet_targets


def _any_formula_changed(
    zin: zipfile.ZipFile,
    sheet_targets: dict[str, str],
    cell_edits_by_sheet: dict,
    rename_map: dict,
) -> bool:
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


def apply_edits(
    input_path: str | Path, output_path: str | Path, edits: Sequence[Edit]
) -> None:
    cell_edits_by_sheet = defaultdict(list)
    rename_map = {}
    dimension_map = {}
    deleted_defined_names = set()
    deleted_sheets = set()

    for edit in edits:
        if isinstance(edit, CellEdit):
            cell_edits_by_sheet[edit.sheet].append(edit)
        elif (
            isinstance(edit, SheetEdit)
            and edit.op == "RenameSheet"
            and edit.new_name is not None
        ):
            rename_map[edit.sheet] = edit.new_name
        elif (
            isinstance(edit, SheetEdit)
            and edit.op == "SetDimension"
            and edit.dimension is not None
        ):
            dimension_map[edit.sheet] = edit.dimension
        elif isinstance(edit, SheetEdit) and edit.op == "DeleteSheet":
            deleted_sheets.add(edit.sheet)
        elif isinstance(edit, WorkbookEdit) and edit.op == "DeleteDefinedName":
            deleted_defined_names.add(edit.name)

    with zipfile.ZipFile(input_path, "r") as zin:
        sheet_targets = get_sheet_targets(zin)
        deleted_targets = {
            sheet_targets[name] for name in deleted_sheets if name in sheet_targets
        }

        calc_chain_dropped = _any_formula_changed(
            zin, sheet_targets, cell_edits_by_sheet, rename_map
        )

        has_style_edits = any(
            isinstance(e, CellEdit) and e.op in ("SetNumFmt", "SetFont") for e in edits
        )
        original_s: dict[tuple[str, str], int] = {}
        new_s_map: dict[tuple[str, str], int] = {}
        styles_xml_bytes: bytes | None = None

        if has_style_edits:
            from backend.workbook.styles import ensure_font_xf

            for sheet_name, sheet_edits in cell_edits_by_sheet.items():
                style_refs = {
                    e.ref for e in sheet_edits if e.op in ("SetNumFmt", "SetFont")
                }
                if not style_refs:
                    continue
                target = sheet_targets.get(sheet_name)
                if not target or target not in zin.namelist():
                    continue
                with zin.open(target) as f:
                    root = etree.parse(f).getroot()
                ns = _ns(root, SPREADSHEET_NS)
                for c_node in root.iter(f"{ns}c"):
                    ref = c_node.get("r")
                    if ref in style_refs:
                        original_s[(sheet_name, ref)] = int(c_node.get("s", "0"))

            if "xl/styles.xml" in zin.namelist():
                with zin.open("xl/styles.xml") as f:
                    tree = etree.parse(f)
                root = tree.getroot()
                ns = _ns(root, SPREADSHEET_NS)
                for sheet_name, sheet_edits in cell_edits_by_sheet.items():
                    for edit in sheet_edits:
                        if edit.op == "SetNumFmt" and edit.num_fmt_code:
                            old_s = original_s.get((sheet_name, edit.ref), 0)
                            new_s = ensure_xf(root, ns, old_s, edit.num_fmt_code)
                            new_s_map[(sheet_name, edit.ref)] = new_s
                        elif edit.op == "SetFont":
                            old_s = original_s.get((sheet_name, edit.ref), 0)
                            new_s = ensure_font_xf(
                                root, ns, old_s, edit.font_name, edit.font_size
                            )
                            new_s_map[(sheet_name, edit.ref)] = new_s
                styles_xml_bytes = etree.tostring(
                    tree, xml_declaration=True, encoding="UTF-8", standalone=True
                )

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

                if item.filename in deleted_targets:
                    continue

                # If this item is a sheet XML, we must check if we need to apply CellEdits OR RenameMap (update references)
                target_sheet_name = next(
                    (
                        name
                        for name, target in sheet_targets.items()
                        if target == item.filename
                    ),
                    None,
                )
                if target_sheet_name is not None:
                    sheet_name_str: str = target_sheet_name
                    has_cell_edits = sheet_name_str in cell_edits_by_sheet
                    has_renames = len(rename_map) > 0
                    has_dimension_edits = sheet_name_str in dimension_map

                    if has_cell_edits or has_renames or has_dimension_edits:
                        sheet_edits = cell_edits_by_sheet.get(sheet_name_str, [])
                        new_dimension = dimension_map.get(sheet_name_str)

                        def mutate_sheet(
                            root,
                            ns,
                            sheet_edits=sheet_edits,
                            rename_map=rename_map,
                            has_renames=has_renames,
                            sheet_name=sheet_name_str,
                            new_s_map=new_s_map,
                            new_dimension=new_dimension,
                        ):
                            if new_dimension is not None:
                                dim_node = root.find(f"{ns}dimension")
                                if dim_node is not None:
                                    dim_node.set("ref", new_dimension)

                            for c_node in root.iter(f"{ns}c"):
                                ref = c_node.get("r")

                                # First, apply formula updates due to renames
                                if has_renames:
                                    f_node = c_node.find(f"{ns}f")
                                    if f_node is not None and f_node.text is not None:
                                        new_f: str = f_node.text
                                        for old_name, new_name in rename_map.items():
                                            new_f = rename_sheet_in_formula(
                                                new_f, old_name, new_name
                                            )
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
                                            is_node = etree.SubElement(
                                                c_node, f"{ns}is"
                                            )
                                            t_node = etree.SubElement(is_node, f"{ns}t")
                                            t_node.text = str(edit.value)
                                        else:
                                            v_node = etree.SubElement(c_node, f"{ns}v")
                                            v_node.text = str(edit.value)

                                    elif edit.op == "SetFormula":
                                        _clear_cell_children(c_node, ns)
                                        f_node = etree.SubElement(c_node, f"{ns}f")
                                        f_node.text = str(edit.formula)

                                    elif edit.op in ("SetNumFmt", "SetFont"):
                                        new_s = new_s_map.get((sheet_name, edit.ref))
                                        if new_s is not None:
                                            c_node.set("s", str(new_s))

                                    elif edit.op == "ClearCell":
                                        _clear_cell_children(c_node, ns)

                        _rewrite_xml_part(zin, zout, item, SPREADSHEET_NS, mutate_sheet)
                        continue

                if item.filename == "xl/workbook.xml":

                    def mutate_workbook(
                        root,
                        ns,
                        rename_map=rename_map,
                        deleted_defined_names=deleted_defined_names,
                        deleted_sheets=deleted_sheets,
                    ):
                        calc_pr = root.find(f"{ns}calcPr")
                        if calc_pr is None:
                            calc_pr = etree.SubElement(root, f"{ns}calcPr")
                        calc_pr.set("fullCalcOnLoad", "1")

                        # Apply renames and deletions to <sheet> elements
                        if rename_map or deleted_sheets:
                            sheets_node = root.find(f"{ns}sheets")
                            if sheets_node is not None:
                                for sheet_node in list(sheets_node.iter(f"{ns}sheet")):
                                    name = sheet_node.get("name")
                                    if name in deleted_sheets:
                                        sheet_node.getparent().remove(sheet_node)
                                    elif name in rename_map:
                                        sheet_node.set("name", rename_map[name])

                            # Apply renames and deletions to <definedName> elements
                            defined_names = root.find(f"{ns}definedNames")
                            if defined_names is not None:
                                for dn in list(defined_names.iter(f"{ns}definedName")):
                                    dn_name = dn.get("name")
                                    if dn_name in deleted_defined_names:
                                        dn.getparent().remove(dn)
                                        continue

                                    if dn.text:
                                        new_text = dn.text
                                        for old_name, new_name in rename_map.items():
                                            new_text = rename_sheet_in_formula(
                                                new_text, old_name, new_name
                                            )
                                        dn.text = new_text

                    _rewrite_xml_part(zin, zout, item, SPREADSHEET_NS, mutate_workbook)
                    continue

                if item.filename == "xl/styles.xml" and styles_xml_bytes is not None:
                    zout.writestr(
                        item, styles_xml_bytes, compress_type=item.compress_type
                    )
                    continue


                if (
                    calc_chain_dropped or deleted_targets
                ) and item.filename == "[Content_Types].xml":

                    def mutate_content_types(root, ns, deleted_targets=deleted_targets):
                        for override in list(root.iter(f"{ns}Override")):
                            part = override.get("PartName")
                            if calc_chain_dropped and part == "/xl/calcChain.xml":
                                override.getparent().remove(override)
                                continue
                            if (
                                deleted_targets
                                and part
                                and part.lstrip("/") in deleted_targets
                            ):
                                override.getparent().remove(override)

                    _rewrite_xml_part(
                        zin, zout, item, CONTENT_TYPES_NS, mutate_content_types
                    )
                    continue

                if (
                    calc_chain_dropped or deleted_targets
                ) and item.filename == "xl/_rels/workbook.xml.rels":

                    def mutate_rels(root, ns, deleted_targets=deleted_targets):
                        for rel in list(root.iter(f"{ns}Relationship")):
                            target = rel.get("Target")
                            if calc_chain_dropped and target in (
                                "calcChain.xml",
                                "/xl/calcChain.xml",
                            ):
                                rel.getparent().remove(rel)
                                continue
                            if (
                                deleted_targets
                                and target
                                and f"xl/{target}" in deleted_targets
                            ):
                                rel.getparent().remove(rel)

                    _rewrite_xml_part(zin, zout, item, RELATIONSHIPS_NS, mutate_rels)
                    continue

                zout.writestr(
                    item, zin.read(item.filename), compress_type=item.compress_type
                )
