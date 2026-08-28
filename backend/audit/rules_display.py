import re
from collections import Counter

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
                            risk=self.risk,
                        )
                    )
        return findings

    def fix(self, wb: WorkbookModel, finding: Finding) -> list[CellEdit]:
        return [
            CellEdit(
                op="SetNumFmt",
                sheet=finding.sheet,
                ref=finding.ref,
                num_fmt_code="dd/mm/yyyy",
            )
        ]


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
                    "_)" in cell.num_fmt
                    or "\\(" in cell.num_fmt
                    or re.search(r"\[\$-[^\]]+\]", cell.num_fmt)
                    or "[Red]" in cell.num_fmt
                ):
                    findings.append(
                        Finding(
                            rule_id=self.id,
                            sheet=sheet_name,
                            ref=ref,
                            description=f"Fragile format code '{cell.num_fmt}'",
                            severity=self.severity,
                            risk=self.risk,
                        )
                    )
        return findings

    def fix(self, wb: WorkbookModel, finding: Finding) -> list[CellEdit]:
        cell = wb.sheets[finding.sheet].cells[finding.ref]
        if not cell.num_fmt:
            return []
        new_fmt = cell.num_fmt
        new_fmt = new_fmt.replace("_)", "")
        new_fmt = new_fmt.replace("\\(", "(")
        new_fmt = new_fmt.replace("\\)", ")")
        new_fmt = re.sub(r"\[\$-[^\]]+\]", "", new_fmt)
        new_fmt = new_fmt.replace("[Red]", "")
        return [
            CellEdit(
                op="SetNumFmt",
                sheet=finding.sheet,
                ref=finding.ref,
                num_fmt_code=new_fmt,
            )
        ]


class RuleR19(Rule):
    id = "R19"
    title = "Inconsistent fonts"
    why = "A single cohesive font makes a spreadsheet look professional. Minor deviations (e.g., Arial 10 vs Arial 11) look accidental and messy."
    severity = "style"
    risk = "display"
    auto_fixable = True

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []

        font_counts: Counter[tuple[str | None, str | None]] = Counter()
        total_cells = 0
        for sheet in wb.sheets.values():
            for cell in sheet.cells.values():
                if cell.font_name is not None or cell.font_size is not None:
                    font_counts[(cell.font_name, cell.font_size)] += 1
                total_cells += 1

        if not font_counts or total_cells == 0:
            return []

        majority_font, _ = font_counts.most_common(1)[0]

        threshold = total_cells * 0.01

        minority_fonts = {
            f
            for f, count in font_counts.items()
            if count < threshold and f != majority_font
        }

        if not minority_fonts:
            return []

        for sheet_name, sheet in wb.sheets.items():
            for ref, cell in sheet.cells.items():
                font_tup = (cell.font_name, cell.font_size)
                if font_tup in minority_fonts:
                    findings.append(
                        Finding(
                            rule_id=self.id,
                            sheet=sheet_name,
                            ref=ref,
                            description=f"Minority font: {font_tup[0]} {font_tup[1]}",
                            severity=self.severity,
                            risk=self.risk,
                        )
                    )
        return findings

    def fix(self, wb: WorkbookModel, finding: Finding) -> list[CellEdit]:
        font_counts: Counter[tuple[str | None, str | None]] = Counter()
        for sheet in wb.sheets.values():
            for c in sheet.cells.values():
                if c.font_name is not None or c.font_size is not None:
                    font_counts[(c.font_name, c.font_size)] += 1

        if not font_counts:
            return []

        majority_font, _ = font_counts.most_common(1)[0]

        return [
            CellEdit(
                op="SetFont",
                sheet=finding.sheet,
                ref=finding.ref,
                font_name=majority_font[0],
                font_size=majority_font[1],
            )
        ]


registry.register(RuleR17())
registry.register(RuleR18())
registry.register(RuleR19())
