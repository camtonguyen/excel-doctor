from pydantic import BaseModel
from typing import Literal, Any

class WorkbookInventory(BaseModel):
    """Tracks features found in the workbook that dictate whether tier A patching is required."""
    has_charts: bool = False
    has_drawings: bool = False
    has_media: bool = False
    has_pivot_tables: bool = False
    has_pivot_caches: bool = False
    has_macros: bool = False
    has_threaded_comments: bool = False
    has_persons: bool = False
    has_tables: bool = False
    has_external_links: bool = False
    has_x14_conditional_formatting: bool = False
    has_sparklines: bool = False
    has_form_controls: bool = False
    has_activex: bool = False

    @property
    def requires_tier_a(self) -> bool:
        """Returns True if any features are present that openpyxl would drop."""
        return any([
            self.has_charts,
            self.has_drawings,
            self.has_media,
            self.has_pivot_tables,
            self.has_pivot_caches,
            self.has_macros,
            self.has_threaded_comments,
            self.has_persons,
            self.has_tables,
            self.has_external_links,
            self.has_x14_conditional_formatting,
            self.has_sparklines,
            self.has_form_controls,
            self.has_activex,
        ])

class Finding(BaseModel):
    rule_id: str
    sheet: str
    ref: str
    description: str
    severity: Literal["error", "warning", "style"]
    risk: Literal["safe", "display", "value"]

class CellEdit(BaseModel):
    op: Literal["SetValue", "SetFormula", "SetNumFmt", "ClearCell"]
    sheet: str
    ref: str
    value: Any = None
    cell_type: str | None = None
    formula: str | None = None
    num_fmt_code: str | None = None

class DiffEntry(BaseModel):
    sheet: str
    ref: str
    before: Any
    after: Any
    cause: str
    note: str
