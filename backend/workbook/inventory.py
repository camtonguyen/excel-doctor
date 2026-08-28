import zipfile
from pathlib import Path

from backend.model import WorkbookInventory


def get_inventory(file_path: str | Path) -> WorkbookInventory:
    """
    Scans the zip entries of an xlsx file to determine its contents
    and whether it requires tier A patching.
    """
    inventory = WorkbookInventory()

    with zipfile.ZipFile(file_path, "r") as z:
        namelist = z.namelist()

        for name in namelist:
            if name.startswith("xl/charts/"):
                inventory.has_charts = True
            elif name.startswith("xl/drawings/"):
                inventory.has_drawings = True
            elif name.startswith("xl/media/"):
                inventory.has_media = True
            elif name.startswith("xl/pivotTables/"):
                inventory.has_pivot_tables = True
            elif name.startswith("xl/pivotCache/"):
                inventory.has_pivot_caches = True
            elif name == "xl/vbaProject.bin":
                inventory.has_macros = True
            elif name.startswith("xl/threadedComments/"):
                inventory.has_threaded_comments = True
            elif name.startswith("xl/persons/"):
                inventory.has_persons = True
            elif name.startswith("xl/tables/"):
                inventory.has_tables = True
            elif name.startswith("xl/externalLinks/"):
                inventory.has_external_links = True
            # Sparklines and form controls usually appear in workbook.xml or worksheet xmls,
            # but their presence often corresponds to specific drawing or extLst parts.
            # We'll leave them as False for now until we parse [Content_Types].xml deeply
            # if needed for those specific features.

    return inventory
