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
                        sheet_targets[rel.get("Id")] = "xl/" + rel.get("Target")
                        
        if "xl/workbook.xml" in z.namelist():
            with z.open("xl/workbook.xml") as f:
                tree = etree.parse(f)
                for sheet in tree.getroot().iter("{*}sheet"):
                    name = sheet.get("name")
                    r_id = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                    target = sheet_targets.get(r_id)
                    if name and target:
                        wb.sheets[name] = SheetModel(name=name, target=target)
                        
        # 3. Parse cells from each worksheet
        for sheet_model in wb.sheets.values():
            if sheet_model.target in z.namelist():
                with z.open(sheet_model.target) as f:
                    tree = etree.parse(f)
                    for c_node in tree.getroot().iter("{*}c"):
                        ref = c_node.get("r")
                        t = c_node.get("t")
                        v_node = c_node.find("{*}v")
                        f_node = c_node.find("{*}f")
                        
                        v = (v_node.text or "") if v_node is not None else None
                        formula = f_node.text if f_node is not None else None
                        
                        sheet_model.cells[ref] = CellModel(ref=ref, t=t, v=v, f=formula)
                        
    return wb
