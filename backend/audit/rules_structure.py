import re

from backend.audit.base import Rule, registry
from backend.model import Edit, Finding, SheetEdit
from backend.workbook.reader import WorkbookModel

_INVALID_CHARS_RE = re.compile(r"[\[\]:\\/\?\*,\.']")

def _is_invalid(sheet_name: str) -> bool:
    if len(sheet_name) > 31:
        return True
    if sheet_name != sheet_name.strip():
        return True
    return bool(_INVALID_CHARS_RE.search(sheet_name))

def _generate_safe_name(wb: WorkbookModel, sheet_name: str) -> str:
    # Strip leading/trailing spaces
    safe = sheet_name.strip()
    
    # Replace invalid chars with underscore
    safe = _INVALID_CHARS_RE.sub("_", safe)
    
    # Truncate to 31 chars
    safe = safe[:31].strip("_")
    if not safe:
        safe = "Sheet"
        
    # Handle collisions
    existing_names = {s.lower() for s in wb.sheets}
    if safe.lower() == sheet_name.lower() or safe.lower() not in existing_names:
        return safe
        
    base = safe[:28] # leave room for " 1" to " 99"
    i = 1
    while f"{base} {i}".lower() in existing_names:
        i += 1
    return f"{base} {i}"

class RuleR15(Rule):
    id = "R15"
    title = "Sheet name contains special characters"
    why = "Tên sheet có ký tự đặc biệt sẽ gây lỗi khi dùng trong công thức (phải thêm dấu nháy đơn), hoặc làm hỏng file."
    severity = "error"
    risk = "safe"
    auto_fixable = True

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        for sheet_name in wb.sheets:
            if _is_invalid(sheet_name):
                findings.append(Finding(
                    rule_id=self.id,
                    sheet=sheet_name,
                    ref="",
                    description="Tên sheet chứa ký tự đặc biệt, dấu câu, khoảng trắng thừa hoặc quá dài",
                    severity=self.severity,
                    risk=self.risk
                ))
        return findings

    def fix(self, wb: WorkbookModel, finding: Finding) -> list[Edit]:
        new_name = _generate_safe_name(wb, finding.sheet)
        return [SheetEdit(
            op="RenameSheet",
            sheet=finding.sheet,
            new_name=new_name
        )]

registry.register(RuleR15())
