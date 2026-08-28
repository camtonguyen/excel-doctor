from typing import Any, Literal

from pydantic import BaseModel, Field


class CellModel(BaseModel):
    ref: str  # e.g., "A1"
    t: str | None = None  # cell type, e.g., "s" for string, "e" for error
    v: str | None = None  # value
    f: str | None = None  # formula
    num_fmt: str | None = None  # resolved number format string
    font_name: str | None = None
    font_size: str | None = None


class SheetModel(BaseModel):
    name: str
    target: str  # e.g. "worksheets/sheet1.xml"
    cells: dict[str, CellModel] = Field(default_factory=dict)


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
        return any(
            [
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
            ]
        )


class Finding(BaseModel):
    rule_id: str
    sheet: str
    ref: str
    description: str
    severity: Literal["error", "warning", "style"]
    risk: Literal["safe", "display", "value"]


class CellEdit(BaseModel):
    op: Literal["SetValue", "SetFormula", "SetNumFmt", "ClearCell", "SetFont"]
    sheet: str
    ref: str
    value: Any = None
    cell_type: str | None = None
    formula: str | None = None
    num_fmt_code: str | None = None
    font_name: str | None = None
    font_size: str | None = None


class SheetEdit(BaseModel):
    op: Literal["RenameSheet"]
    sheet: str
    new_name: str


Edit = CellEdit | SheetEdit


class DiffEntry(BaseModel):
    sheet: str
    ref: str
    before: Any
    after: Any
    cause: str
    note: str
