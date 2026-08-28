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

    base = safe[:28]  # leave room for " 1" to " 99"
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
                findings.append(
                    Finding(
                        rule_id=self.id,
                        sheet=sheet_name,
                        ref="",
                        description="Tên sheet chứa ký tự đặc biệt, dấu câu, khoảng trắng thừa hoặc quá dài",
                        severity=self.severity,
                        risk=self.risk,
                    )
                )
        return findings

    def fix(self, wb: WorkbookModel, finding: Finding) -> list[Edit]:
        new_name = _generate_safe_name(wb, finding.sheet)
        return [SheetEdit(op="RenameSheet", sheet=finding.sheet, new_name=new_name)]


def _col_to_num(col_str: str) -> int:
    num = 0
    for c in col_str:
        num = num * 26 + (ord(c.upper()) - ord("A") + 1)
    return num


def _num_to_col(n: int) -> str:
    string = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string


def _parse_ref(ref: str) -> tuple[int, int]:
    match = re.match(r"([A-Z]+)(\d+)", ref)
    if not match:
        return 1, 1
    col = _col_to_num(match.group(1))
    row = int(match.group(2))
    return col, row


class RuleR21(Rule):
    id = "R21"
    title = "Bloated used range"
    why = "Declared dimension far exceeds the last cell with content, causing file bloat and performance issues."
    severity = "style"
    risk = "safe"
    auto_fixable = True

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        for sheet_name, sheet in wb.sheets.items():
            if not sheet.dimension or ":" not in sheet.dimension:
                continue

            _, end = sheet.dimension.split(":")
            declared_max_col, declared_max_row = _parse_ref(end)

            if not sheet.cells:
                # If no cells but dimension declared e.g. A1:Z100
                if declared_max_row > 1 or declared_max_col > 1:
                    findings.append(
                        Finding(
                            rule_id=self.id,
                            sheet=sheet_name,
                            ref=sheet.dimension,
                            description=f"Declared dimension {sheet.dimension} for empty sheet.",
                            severity=self.severity,
                            risk=self.risk,
                        )
                    )
                continue

            actual_max_col = 1
            actual_max_row = 1
            for ref in sheet.cells:
                c, r = _parse_ref(ref)
                actual_max_col = max(actual_max_col, c)
                actual_max_row = max(actual_max_row, r)

            if (
                declared_max_row > actual_max_row + 100
                or declared_max_col > actual_max_col + 20
            ):
                findings.append(
                    Finding(
                        rule_id=self.id,
                        sheet=sheet_name,
                        ref=sheet.dimension,
                        description=f"Declared dimension {sheet.dimension} far exceeds actual content (max row {actual_max_row}, max col {_num_to_col(actual_max_col)}).",
                        severity=self.severity,
                        risk=self.risk,
                    )
                )
        return findings

    def fix(self, wb: WorkbookModel, finding: Finding) -> list[Edit]:
        sheet = wb.sheets[finding.sheet]

        if not sheet.cells:
            return [SheetEdit(op="SetDimension", sheet=finding.sheet, dimension="A1")]

        actual_max_col = 1
        actual_max_row = 1
        for ref in sheet.cells:
            c, r = _parse_ref(ref)
            actual_max_col = max(actual_max_col, c)
            actual_max_row = max(actual_max_row, r)

        new_dim = f"A1:{_num_to_col(actual_max_col)}{actual_max_row}"
        return [SheetEdit(op="SetDimension", sheet=finding.sheet, dimension=new_dim)]


class RuleR22(Rule):
    id = "R22"
    title = "Broken defined name"
    why = "Defined names that resolve to #REF! indicate deleted ranges and can cause unexpected errors."
    severity = "warning"
    risk = "safe"
    auto_fixable = True

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        for name, formula in wb.defined_names.items():
            if "#REF!" in formula:
                findings.append(
                    Finding(
                        rule_id=self.id,
                        sheet="Workbook",
                        ref=name,
                        description=f"Defined name '{name}' contains #REF!",
                        severity=self.severity,
                        risk=self.risk,
                    )
                )
        return findings

    def fix(self, wb: WorkbookModel, finding: Finding) -> list[Edit]:
        from backend.model import WorkbookEdit

        return [WorkbookEdit(op="DeleteDefinedName", name=finding.ref)]


registry.register(RuleR15())
registry.register(RuleR21())
registry.register(RuleR22())
