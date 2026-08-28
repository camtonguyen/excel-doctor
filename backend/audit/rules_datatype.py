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


registry.register(RuleR14())
