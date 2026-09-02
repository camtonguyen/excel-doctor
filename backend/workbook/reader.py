import zipfile
from collections.abc import Iterator
from pathlib import Path

from lxml import etree

from backend.model import CellModel, SheetModel, WorkbookInventory
from backend.workbook.inventory import get_inventory


class WorkbookModel:
    """In-memory representation of the parsed Excel file."""

    def __init__(self, inventory: WorkbookInventory):
        self.inventory = inventory
        self.sheets: dict[str, SheetModel] = {}
        self.shared_strings: list[str] = []
        self.defined_names: dict[str, str] = {}

    def iter_cells(self) -> Iterator[tuple[str, str, CellModel]]:
        """Yields (sheet_name, ref, cell) for every cell in every sheet."""
        for sheet_name, sheet in self.sheets.items():
            for ref, cell in sheet.cells.items():
                yield sheet_name, ref, cell

    def resolve_shared_string(self, cell: CellModel) -> str | None:
        """Returns a t="s" cell's text, or None if the cell isn't a shared string
        or its index doesn't resolve."""
        if cell.t != "s" or cell.v is None:
            return None
        try:
            return self.shared_strings[int(cell.v)]
        except (ValueError, IndexError):
            return None


def _strip_ns(tag: str) -> str:
    return tag.split("}")[1] if "}" in tag else tag


def read_workbook(file_path: str | Path) -> WorkbookModel:
    inventory = get_inventory(file_path)
    wb = WorkbookModel(inventory=inventory)

    with zipfile.ZipFile(file_path, "r") as z:
        # 1. Parse shared strings if they exist
        if "xl/sharedStrings.xml" in z.namelist():
            with z.open("xl/sharedStrings.xml") as f:
                tree = etree.parse(f)
                for si in tree.getroot().iter("{*}si"):
                    t_node = si.find("{*}t")
                    text = t_node.text if t_node is not None else ""
                    wb.shared_strings.append(text or "")

        # 2. Parse workbook.xml to get sheet names and rel IDs
        sheet_targets = {}
        if "xl/_rels/workbook.xml.rels" in z.namelist():
            with z.open("xl/_rels/workbook.xml.rels") as f:
                tree = etree.parse(f)
                for rel in tree.getroot().iter("{*}Relationship"):
                    if "worksheet" in rel.get("Type", ""):
                        target_path = rel.get("Target", "")
                        if target_path.startswith("/"):
                            sheet_targets[rel.get("Id")] = target_path.lstrip("/")
                        else:
                            sheet_targets[rel.get("Id")] = "xl/" + target_path

        if "xl/workbook.xml" in z.namelist():
            with z.open("xl/workbook.xml") as f:
                tree = etree.parse(f)
                for sheet in tree.getroot().iter("{*}sheet"):
                    name = sheet.get("name")
                    r_id = sheet.get(
                        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                    )
                    target = sheet_targets.get(r_id)
                    if name and target:
                        wb.sheets[name] = SheetModel(name=name, target=target)

                defined_names_node = tree.getroot().find("{*}definedNames")
                if defined_names_node is not None:
                    for dn in defined_names_node.iter("{*}definedName"):
                        dn_name = dn.get("name")
                        if dn_name and dn.text:
                            wb.defined_names[dn_name] = dn.text

        # 3. Parse styles to map cell format index to actual number format string
        cell_xfs_num_fmt_ids = []
        cell_xfs_font_ids = []
        custom_num_fmts = {}
        fonts = {}  # id -> (name, size)
        if "xl/styles.xml" in z.namelist():
            with z.open("xl/styles.xml") as f:
                tree = etree.parse(f)
                root = tree.getroot()

                # Extract custom numFmts
                numFmts_node = root.find("{*}numFmts")
                if numFmts_node is not None:
                    for numFmt in numFmts_node.iter("{*}numFmt"):
                        fmt_id = int(numFmt.get("numFmtId", "0"))
                        code = numFmt.get("formatCode", "")
                        custom_num_fmts[fmt_id] = code

                # Extract fonts
                fonts_node = root.find("{*}fonts")
                if fonts_node is not None:
                    for i, font in enumerate(fonts_node.iter("{*}font")):
                        name_node = font.find("{*}name")
                        sz_node = font.find("{*}sz")
                        name = name_node.get("val") if name_node is not None else None
                        sz = sz_node.get("val") if sz_node is not None else None
                        fonts[i] = (name, sz)

                # Extract cellXfs
                cellXfs_node = root.find("{*}cellXfs")
                if cellXfs_node is not None:
                    for xf in cellXfs_node.iter("{*}xf"):
                        cell_xfs_num_fmt_ids.append(int(xf.get("numFmtId", "0")))
                        cell_xfs_font_ids.append(int(xf.get("fontId", "0")))

        # Define basic built-in formats (dates, percentages, numeric, etc.)
        BUILTIN_FMTS = {
            1: "0",
            2: "0.00",
            3: "#,##0",
            4: "#,##0.00",
            9: "0%",
            10: "0.00%",
            11: "0.00E+00",
            12: "# ?/?",
            13: "# ??/??",
            14: "m/d/yyyy",
            15: "d-mmm-yy",
            16: "d-mmm",
            17: "mmm-yy",
            22: "m/d/yyyy h:mm",
            37: "#,##0 ;(#,##0)",
            38: "#,##0 ;[Red](#,##0)",
            39: "#,##0.00;(#,##0.00)",
            40: "#,##0.00;[Red](#,##0.00)",
            49: "@",
        }


        # 4. Parse cells from each worksheet
        for sheet_model in wb.sheets.values():
            if sheet_model.target in z.namelist():
                with z.open(sheet_model.target) as f:
                    tree = etree.parse(f)
                    root = tree.getroot()

                    dim_node = root.find("{*}dimension")
                    if dim_node is not None:
                        sheet_model.dimension = dim_node.get("ref")

                    for c_node in root.iter("{*}c"):
                        ref = c_node.get("r")
                        t = c_node.get("t")
                        s_idx = int(c_node.get("s", "0"))

                        v_node = c_node.find("{*}v")
                        f_node = c_node.find("{*}f")

                        v = (v_node.text or "") if v_node is not None else None
                        if v is None and t == "inlineStr":
                            is_node = c_node.find("{*}is")
                            if is_node is not None:
                                t_node = is_node.find("{*}t")
                                if t_node is not None:
                                    v = t_node.text or ""
                        formula = f_node.text if f_node is not None else None

                        num_fmt = None
                        font_name = None
                        font_size = None
                        if s_idx < len(cell_xfs_num_fmt_ids):
                            fmt_id = cell_xfs_num_fmt_ids[s_idx]
                            num_fmt = custom_num_fmts.get(fmt_id) or BUILTIN_FMTS.get(
                                fmt_id
                            )
                        if s_idx < len(cell_xfs_font_ids):
                            f_id = cell_xfs_font_ids[s_idx]
                            font_name, font_size = fonts.get(f_id, (None, None))

                        sheet_model.cells[ref] = CellModel(
                            ref=ref,
                            t=t,
                            v=v,
                            f=formula,
                            num_fmt=num_fmt,
                            font_name=font_name,
                            font_size=font_size,
                        )

    return wb
