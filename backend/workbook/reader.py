from pathlib import Path
from backend.workbook.inventory import get_inventory
from backend.model import WorkbookInventory

class WorkbookModel:
    """In-memory representation of the parsed Excel file."""
    def __init__(self, inventory: WorkbookInventory):
        self.inventory = inventory
        # TODO: Add sheets, strings, styles, etc.

def read_workbook(file_path: str | Path) -> WorkbookModel:
    """
    Reads an xlsx file, starting with its inventory to determine structure,
    then parses the XML content into a WorkbookModel.
    """
    inventory = get_inventory(file_path)
    wb = WorkbookModel(inventory=inventory)
    
    # TODO: Implement zip extraction and parsing sheets/strings/styles
    
    return wb
