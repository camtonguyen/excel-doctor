from backend.audit.base import Rule, registry
from backend.model import Finding
from backend.workbook.formula import TokenType, tokenize
from backend.workbook.reader import WorkbookModel


class RuleR01(Rule):
    id = "R01"
    title = "Formula contains #REF!"
    why = "A cell was deleted that this formula depended on."
    severity = "error"
    risk = "value"
    auto_fixable = False

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        for sheet_name, ref, cell in wb.iter_cells():
            if cell.f and "#REF!" in cell.f:
                findings.append(
                    Finding(
                        rule_id=self.id,
                        sheet=sheet_name,
                        ref=ref,
                        description="Formula contains #REF!",
                        severity=self.severity,
                        risk=self.risk,
                    )
                )
        return findings


class RuleR02(Rule):
    id = "R02"
    title = "Cell currently evaluates to an error"
    why = "The cached value of the cell is an error type."
    severity = "error"
    risk = "value"
    auto_fixable = False

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        for sheet_name, ref, cell in wb.iter_cells():
            if cell.t == "e" or (
                cell.v and str(cell.v).startswith("#") and str(cell.v).endswith("!")
            ):
                findings.append(
                    Finding(
                        rule_id=self.id,
                        sheet=sheet_name,
                        ref=ref,
                        description=f"Cell evaluates to error: {cell.v}",
                        severity=self.severity,
                        risk=self.risk,
                    )
                )
        return findings


class RuleR03(Rule):
    id = "R03"
    title = "Error code pasted in as literal text"
    why = "Values were pasted as text without formulas, carrying over an error."
    severity = "error"
    risk = "value"
    auto_fixable = True

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        error_strings = {
            "#REF!",
            "#VALUE!",
            "#N/A",
            "#NAME?",
            "#DIV/0!",
            "#NUM!",
            "#NULL!",
            "#ERROR!",
        }
        for sheet_name, ref, cell in wb.iter_cells():
            if cell.f:
                continue
            text = wb.resolve_shared_string(cell)
            if text in error_strings:
                findings.append(
                    Finding(
                        rule_id=self.id,
                        sheet=sheet_name,
                        ref=ref,
                        description="Error code pasted as literal text",
                        severity=self.severity,
                        risk=self.risk,
                    )
                )
        return findings


class RuleR04(Rule):
    id = "R04"
    title = "Arithmetic directly on a cell that returns empty string"
    why = (
        "Doing A1*2 when A1 is '' returns #VALUE!. It is the most common hidden defect."
    )
    severity = "error"
    risk = "display"
    auto_fixable = True

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        # Pre-compute cells that return ""
        empty_cells: dict[str, set[str]] = {}
        for sheet_name, ref, cell in wb.iter_cells():
            # A cell that is type "str" and value ""
            if cell.t == "str" and cell.v == "":
                empty_cells.setdefault(sheet_name, set()).add(ref)

        # Now detect arithmetic on those cells
        for sheet_name, ref, cell in wb.iter_cells():
            if cell.f:
                tokens = tokenize(cell.f)
                ops = [
                    t.value
                    for t in tokens
                    if t.type == TokenType.OPERATOR and t.value in "+-*/"
                ]
                if ops:
                    # Check operands
                    for t in tokens:
                        if t.type == TokenType.OPERAND and t.value in empty_cells.get(
                            sheet_name, set()
                        ):
                            findings.append(
                                Finding(
                                    rule_id=self.id,
                                    sheet=sheet_name,
                                    ref=ref,
                                    description=f"Arithmetic operation on cell {t.value} which evaluates to empty string",
                                    severity=self.severity,
                                    risk=self.risk,
                                )
                            )
                            break
        return findings


class RuleR05(Rule):
    id = "R05"
    title = "Reference to a sheet that doesn't exist"
    why = "Formula references a deleted or missing sheet."
    severity = "error"
    risk = "value"
    auto_fixable = False

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        sheet_names = set(wb.sheets.keys())
        for sheet_name, ref, cell in wb.iter_cells():
            if cell.f:
                tokens = tokenize(cell.f)
                for t in tokens:
                    if t.type == TokenType.OPERAND and "!" in t.value:
                        target_sheet = t.value.split("!")[0].strip("'")
                        if (
                            target_sheet not in sheet_names
                            and not target_sheet.startswith("#")
                        ):
                            findings.append(
                                Finding(
                                    rule_id=self.id,
                                    sheet=sheet_name,
                                    ref=ref,
                                    description=f"References missing sheet: {target_sheet}",
                                    severity=self.severity,
                                    risk=self.risk,
                                )
                            )
        return findings


class RuleR20(Rule):
    id = "R20"
    title = "Functions only available in newer Excel"
    why = "Functions like XLOOKUP or FILTER cause #NAME? errors when the workbook is opened in older versions of Excel."
    severity = "warning"
    risk = "safe"
    auto_fixable = False

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        newer_funcs = {
            "XLOOKUP",
            "XMATCH",
            "FILTER",
            "UNIQUE",
            "SORTBY",
            "SEQUENCE",
            "LET",
            "LAMBDA",
            "TEXTJOIN",
            "IFS",
            "SWITCH",
            "MAXIFS",
            "MINIFS",
            "CONCAT",
        }
        for sheet_name, ref, cell in wb.iter_cells():
            if cell.f:
                tokens = tokenize(cell.f)
                for t in tokens:
                    if (
                        t.type == TokenType.FUNCTION
                        and t.value.upper().rstrip("(") in newer_funcs
                    ):
                        findings.append(
                            Finding(
                                rule_id=self.id,
                                sheet=sheet_name,
                                ref=ref,
                                description=f"Formula uses newer Excel function {t.value.upper().rstrip('(')}. Consider using alternatives.",
                                severity=self.severity,
                                risk=self.risk,
                            )
                        )
                        break
        return findings


registry.register(RuleR01())
registry.register(RuleR02())
registry.register(RuleR03())
registry.register(RuleR04())
registry.register(RuleR05())
registry.register(RuleR20())
