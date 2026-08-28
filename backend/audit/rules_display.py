import re

from backend.audit.base import Rule, registry
from backend.model import CellEdit, Finding
from backend.workbook.reader import WorkbookModel

# Matches optional [$-xxx] prefix, followed by either mm-dd or m/d/yy
_AMBIGUOUS_DATE_RE = re.compile(r"^(?:\[\$[^\]]+\])?(mm-dd|m/d/yy)", re.IGNORECASE)

class RuleR17(Rule):
    id = "R17"
    title = "Locale-ambiguous date format"
    why = "Locale-ambiguous date formats like mm-dd or m/d/yy display differently depending on system region settings, leading to confusion."
    severity = "style"
    risk = "display"
    auto_fixable = True

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        for sheet_name, sheet in wb.sheets.items():
            for ref, cell in sheet.cells.items():
                if cell.num_fmt and _AMBIGUOUS_DATE_RE.match(cell.num_fmt):
                    findings.append(
                            Finding(
                                rule_id=self.id,
                                sheet=sheet_name,
                                ref=ref,
                                description=f"Ambiguous date format '{cell.num_fmt}'",
                                severity=self.severity,
                                risk=self.risk
                            )
                        )
        return findings

    def fix(self, wb: WorkbookModel, finding: Finding) -> list[CellEdit]:
        return [CellEdit(
            op="SetNumFmt",
            sheet=finding.sheet,
            ref=finding.ref,
            num_fmt_code="dd/mm/yyyy"
        )]
class RuleR18(Rule):
    id = "R18"
    title = "Fragile format code"
    why = "Format codes with locale-specific prefixes or unusual escaping can break when opened in different regions or older spreadsheet software."
    severity = "style"
    risk = "display"
    auto_fixable = True

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        for sheet_name, sheet in wb.sheets.items():
            for ref, cell in sheet.cells.items():
                if cell.num_fmt and (
                    "_)" in cell.num_fmt or 
                    "\\(" in cell.num_fmt or 
                    re.search(r"\[\$-[^\]]+\]", cell.num_fmt) or
                    "[Red]" in cell.num_fmt
                ):
                    findings.append(
                        Finding(
                            rule_id=self.id,
                            sheet=sheet_name,
                            ref=ref,
                            description=f"Fragile format code '{cell.num_fmt}'",
                            severity=self.severity,
                            risk=self.risk
                        )
                    )
        return findings

    def fix(self, wb: WorkbookModel, finding: Finding) -> list[CellEdit]:
        cell = wb.sheets[finding.sheet].cells[finding.ref]
        new_fmt = cell.num_fmt
        new_fmt = new_fmt.replace("_)", "")
        new_fmt = new_fmt.replace("\\(", "(")
        new_fmt = new_fmt.replace("\\)", ")")
        new_fmt = re.sub(r"\[\$-[^\]]+\]", "", new_fmt)
        new_fmt = new_fmt.replace("[Red]", "")
        return [CellEdit(
            op="SetNumFmt",
            sheet=finding.sheet,
            ref=finding.ref,
            num_fmt_code=new_fmt
        )]

registry.register(RuleR17())
registry.register(RuleR18())
