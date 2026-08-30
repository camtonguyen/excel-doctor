import datetime
import re
import unicodedata

from backend.audit.base import Rule, registry
from backend.model import CellEdit, Finding
from backend.workbook.reader import WorkbookModel

_NBSP = "\u00a0"
_ZERO_WIDTH = "\u200b\u200c\ufeff\u200e\u200f"


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace(_NBSP, " ")
    for ch in _ZERO_WIDTH:
        text = text.replace(ch, "")
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def _parse_date_from_text(text: str) -> int | None:
    s = _clean(text)
    if not s:
        return None

    match = re.match(r"^(\d{1,2})([/.-])(\d{1,2})\2(\d{2}|\d{4})$", s)
    if not match:
        return None

    d_str, _sep, m_str, y_str = match.groups()
    day = int(d_str)
    month = int(m_str)
    year = int(y_str)

    if len(y_str) == 2:
        if year < 50:
            year += 2000
        else:
            year += 1900

    if not (1900 <= year <= 2100):
        return None

    try:
        dt = datetime.date(year, month, day)
    except ValueError:
        return None

    if dt >= datetime.date(1900, 3, 1):
        return (dt - datetime.date(1899, 12, 30)).days
    elif dt >= datetime.date(1900, 1, 1):
        return (dt - datetime.date(1899, 12, 31)).days + 1
    return None


def _parse_number_from_text(text: str) -> int | float | None:
    if _parse_date_from_text(text) is not None:
        return None
    s = text.strip()
    if not s:
        return None


    sign = 1
    if s.startswith("-"):
        sign = -1
        s = s[1:].strip()
    elif s.startswith("+"):
        s = s[1:].strip()
    elif s.startswith("(") and s.endswith(")"):
        sign = -1
        s = s[1:-1].strip()

    if not s:
        return None

    # Only digits, dots, commas, spaces allowed
    if not re.match(r"^[\d\s.,]+$", s):
        return None

    # Remove internal spaces (e.g. "1 000 000" or "1 234,56")
    s_nospace = s.replace(" ", "")
    if not s_nospace or not any(c.isdigit() for c in s_nospace):
        return None

    # Pure digits
    if s_nospace.isdigit():
        # Prevent phone numbers / codes with leading zeros (e.g. "090123", "0123")
        # unless it is literally "0"
        if len(s_nospace) > 1 and s_nospace.startswith("0"):
            return None
        return int(s_nospace) * sign

    has_comma = "," in s_nospace
    has_dot = "." in s_nospace

    if has_comma and has_dot:
        last_comma = s_nospace.rfind(",")
        last_dot = s_nospace.rfind(".")
        if last_dot > last_comma:
            # US style: 1,234.56 or 1,234,567.89
            clean_s = s_nospace.replace(",", "")
        else:
            # EU/VN style: 1.234,56 or 1.234.567,89
            clean_s = s_nospace.replace(".", "").replace(",", ".")
    elif has_comma:
        if s_nospace.count(",") > 1:
            clean_s = s_nospace.replace(",", "")
        else:
            parts = s_nospace.split(",")
            if len(parts[1]) == 3 and len(parts[0]) in (1, 2, 3):
                # Ambiguous thousands separator like 1,234 vs decimal 1,23
                clean_s = s_nospace.replace(",", "")
            else:
                clean_s = s_nospace.replace(",", ".")
    elif has_dot:
        if s_nospace.count(".") > 1:
            clean_s = s_nospace.replace(".", "")
        else:
            clean_s = s_nospace
    else:
        clean_s = s_nospace

    try:
        if "." in clean_s:
            return float(clean_s) * sign
        else:
            return int(clean_s) * sign
    except ValueError:
        return None


class RuleR09(Rule):
    id = "R09"
    title = "Số lưu dưới dạng văn bản"
    why = "SUM và SUMIF bỏ qua các ô này. Nhìn thì giống số nhưng không cộng được."
    severity = "warning"
    risk = "value"
    auto_fixable = True

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        for sheet_name, ref, cell in wb.iter_cells():
            if cell.f:
                continue
            text = None
            if cell.t == "s":
                text = wb.resolve_shared_string(cell)
            elif cell.t in ("inlineStr", "str"):
                text = cell.v
            if text is not None:
                parsed = _parse_number_from_text(text)
                if parsed is not None:
                    findings.append(
                        Finding(
                            rule_id=self.id,
                            sheet=sheet_name,
                            ref=ref,
                            description=f"Number '{text}' is stored as text",
                            severity=self.severity,
                            risk=self.risk,
                        )
                    )
        return findings

    def fix(self, wb: WorkbookModel, finding: Finding) -> list[CellEdit]:
        cell = wb.sheets[finding.sheet].cells[finding.ref]
        text = None
        if cell.t == "s":
            text = wb.resolve_shared_string(cell)
        elif cell.t in ("inlineStr", "str"):
            text = cell.v
        assert text is not None, "fix() requires finding produced by detect()"
        parsed = _parse_number_from_text(text)
        assert parsed is not None, f"Text '{text}' could not be parsed as number"
        return [
            CellEdit(
                op="SetValue",
                sheet=finding.sheet,
                ref=finding.ref,
                value=parsed,
                cell_type=None,
            )
        ]


class RuleR10(Rule):
    id = "R10"
    title = "Ngày tháng lưu dưới dạng văn bản"
    why = "Excel không nhận diện được ngày tháng nên không thể lọc, sắp xếp theo thời gian hoặc tính số ngày."
    severity = "warning"
    risk = "value"
    auto_fixable = True

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        for sheet_name, ref, cell in wb.iter_cells():
            if cell.f:
                continue
            text = None
            if cell.t == "s":
                text = wb.resolve_shared_string(cell)
            elif cell.t in ("inlineStr", "str"):
                text = cell.v
            if text is not None:
                parsed = _parse_date_from_text(text)
                if parsed is not None:
                    findings.append(
                        Finding(
                            rule_id=self.id,
                            sheet=sheet_name,
                            ref=ref,
                            description=f"Date '{text}' is stored as text",
                            severity=self.severity,
                            risk=self.risk,
                        )
                    )
        return findings

    def fix(self, wb: WorkbookModel, finding: Finding) -> list[CellEdit]:
        cell = wb.sheets[finding.sheet].cells[finding.ref]
        text = None
        if cell.t == "s":
            text = wb.resolve_shared_string(cell)
        elif cell.t in ("inlineStr", "str"):
            text = cell.v
        assert text is not None, "fix() requires finding produced by detect()"
        parsed = _parse_date_from_text(text)
        assert parsed is not None, f"Text '{text}' could not be parsed as date"
        return [
            CellEdit(
                op="SetValue",
                sheet=finding.sheet,
                ref=finding.ref,
                value=parsed,
                cell_type=None,
            ),
            CellEdit(
                op="SetNumFmt",
                sheet=finding.sheet,
                ref=finding.ref,
                num_fmt_code="dd/mm/yyyy",
            ),
        ]


class RuleR14(Rule):
    id = "R14"
    title = "Stray whitespace and invisible characters"
    why = "Khoảng trắng thừa hoặc ký tự ẩn khiến so sánh và tra cứu dữ liệu bị sai."
    severity = "style"
    risk = "safe"
    auto_fixable = True

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        for sheet_name, ref, cell in wb.iter_cells():
            text = wb.resolve_shared_string(cell)
            if text is not None and _clean(text) != text:
                findings.append(
                    Finding(
                        rule_id=self.id,
                        sheet=sheet_name,
                        ref=ref,
                        description="Stray whitespace or invisible character in cell text",
                        severity=self.severity,
                        risk=self.risk,
                    )
                )
        return findings

    def fix(self, wb: WorkbookModel, finding: Finding) -> list[CellEdit]:
        cell = wb.sheets[finding.sheet].cells[finding.ref]
        text = wb.resolve_shared_string(cell)
        assert text is not None, "fix() requires a finding produced by detect()"
        return [
            CellEdit(
                op="SetValue",
                sheet=finding.sheet,
                ref=finding.ref,
                value=_clean(text),
                cell_type="inlineStr",
            )
        ]


registry.register(RuleR09())
registry.register(RuleR10())
registry.register(RuleR14())

