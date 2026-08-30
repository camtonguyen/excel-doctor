import re

from backend.audit.base import Rule, registry
from backend.model import CellEdit, CellModel, Edit, Finding
from backend.workbook.formula import TokenType, tokenize
from backend.workbook.reader import WorkbookModel


def _split_ref(ref: str) -> tuple[str, int]:
    match = re.match(r"^([A-Z]+)(\d+)$", ref)
    if match:
        return match.group(1), int(match.group(2))
    return "", 0


def _get_own_column_refs(formula: str, own_col: str) -> list[int]:
    tokens = tokenize(formula)
    rows = []
    for t in tokens:
        if t.type == TokenType.OPERAND:
            val = t.value
            if "!" in val:
                val = val.split("!")[-1]
            for match in re.finditer(r"\b([\$]?[A-Za-z]+)[\$]?(\d+)\b", val):
                ref_str = match.group(1).replace("$", "").upper()
                if ref_str == own_col:
                    rows.append(int(match.group(2)))
    return rows


def _normalize_to_relative(formula: str, base_row: int) -> str:
    tokens = tokenize(formula)
    out = []
    for t in tokens:
        if t.type == TokenType.OPERAND:
            val = t.value

            def repl(m):
                col_part = m.group(1)
                abs_row = m.group(2)
                row_num = int(m.group(3))
                if abs_row == "$":
                    return m.group(0)
                offset = row_num - base_row
                return f"{col_part}[{offset:+d}]" if offset != 0 else f"{col_part}[0]"

            val = re.sub(r"(?<![A-Za-z])([\$]?[A-Za-z]+)([\$]?)(\d+)\b", repl, val)
            out.append(val)
        else:
            out.append(t.value)
    return "".join(out)


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


class RuleR06(Rule):
    id = "R06"
    title = "Running-balance chain skips a row"
    why = "A running balance should reference the cell immediately above it. Skipping a row usually indicates a copy-paste error."
    severity = "warning"
    risk = "value"
    auto_fixable = True

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        for sheet_name, sheet in wb.sheets.items():
            cols: dict[str, list[tuple[int, str, str]]] = {}
            for ref, cell in sheet.cells.items():
                if cell.f:
                    c, r = _split_ref(ref)
                    if c:
                        cols.setdefault(c, []).append((r, ref, cell.f))

            for col, cells in cols.items():
                links = {}
                for r, ref, f in cells:
                    own_col_rows = set(_get_own_column_refs(f, col))
                    if len(own_col_rows) == 1:
                        links[r] = own_col_rows.pop()

                correct_count = sum(1 for r, ref_r in links.items() if ref_r == r - 1)

                if correct_count >= 4:
                    for r, ref, f in cells:
                        if r in links and links[r] != r - 1:
                            findings.append(
                                Finding(
                                    rule_id=self.id,
                                    sheet=sheet_name,
                                    ref=ref,
                                    description=f"Running balance references row {links[r]} instead of row {r - 1}.",
                                    severity=self.severity,
                                    risk=self.risk,
                                )
                            )
        return findings

    def fix(self, wb: WorkbookModel, finding: Finding) -> list[Edit]:
        sheet = wb.sheets[finding.sheet]
        cell = sheet.cells[finding.ref]
        f = cell.f
        c, r = _split_ref(finding.ref)

        if not f:
            return []

        tokens = tokenize(f)
        out = []
        for t in tokens:
            if t.type == TokenType.OPERAND:
                val = t.value

                def repl(m):
                    col_str = m.group(1).replace("$", "").upper()
                    if col_str == c:
                        return f"{m.group(1)}{r - 1}"
                    return m.group(0)

                val = re.sub(r"\b([\$]?[A-Za-z]+[\$]?)\d+\b", repl, val)
                out.append(val)
            else:
                out.append(t.value)
        new_f = "".join(out)

        return [
            CellEdit(
                op="SetFormula", sheet=finding.sheet, ref=finding.ref, formula=new_f
            )
        ]


class RuleR07(Rule):
    id = "R07"
    title = "Empty cell breaks a formula chain"
    why = "An empty cell surrounded by formulas in the same column usually indicates a missing row fill."
    severity = "warning"
    risk = "value"
    auto_fixable = True

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        for sheet_name, sheet in wb.sheets.items():
            cols: dict[str, dict[int, CellModel]] = {}
            for ref, cell in sheet.cells.items():
                c, r = _split_ref(ref)
                if c:
                    cols.setdefault(c, {})[r] = cell

            for col, cells in cols.items():
                f_rows = {r for r, cell in cells.items() if cell.f}
                for r in f_rows:
                    if r + 2 in f_rows and r + 1 not in f_rows:
                        gap_cell = cells.get(r + 1)
                        if gap_cell is None or (
                            not getattr(gap_cell, "f", None)
                            and not getattr(gap_cell, "v", None)
                        ):
                            findings.append(
                                Finding(
                                    rule_id=self.id,
                                    sheet=sheet_name,
                                    ref=f"{col}{r + 1}",
                                    description=f"Empty cell breaks formula chain between {col}{r} and {col}{r + 2}.",
                                    severity=self.severity,
                                    risk=self.risk,
                                )
                            )
        return findings

    def fix(self, wb: WorkbookModel, finding: Finding) -> list[Edit]:
        sheet = wb.sheets[finding.sheet]
        c, r = _split_ref(finding.ref)

        cell_below = sheet.cells.get(f"{c}{r + 1}")
        if not cell_below or not cell_below.f:
            return []

        f_below = cell_below.f

        tokens = tokenize(f_below)
        out = []
        for t in tokens:
            if t.type == TokenType.OPERAND:
                val = t.value

                def repl(m):
                    col_part = m.group(1)
                    abs_row = m.group(2)
                    row_num = int(m.group(3))
                    if abs_row == "$":
                        return m.group(0)
                    new_row = max(1, row_num - 1)
                    return f"{col_part}{abs_row}{new_row}"

                val = re.sub(r"(?<![A-Za-z])([\$]?[A-Za-z]+)([\$]?)(\d+)\b", repl, val)
                out.append(val)
            else:
                out.append(t.value)
        new_f = "".join(out)

        return [
            CellEdit(
                op="SetFormula", sheet=finding.sheet, ref=finding.ref, formula=new_f
            )
        ]


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


class RuleR08(Rule):
    id = "R08"
    title = "Công thức lệch chuẩn trong cột"
    why = "Công thức ô này bị lệch so với các ô khác trong cùng cột. Các dòng trên dưới tính giống nhau, riêng dòng này tính kiểu khác."
    severity = "warning"
    risk = "value"
    auto_fixable = True

    def detect(self, wb: WorkbookModel) -> list[Finding]:
        findings = []
        for sheet_name, sheet in wb.sheets.items():
            cols: dict[str, dict[int, CellModel]] = {}
            for ref, cell in sheet.cells.items():
                if cell.f:
                    c, r = _split_ref(ref)
                    if c:
                        cols.setdefault(c, {})[r] = cell

            for col, cells in cols.items():
                rows = sorted(cells.keys())
                patterns = {
                    r: _normalize_to_relative(f, r)
                    for r in rows
                    if (f := cells[r].f) is not None
                }

                for r in rows:
                    if (
                        r - 1 in patterns
                        and r + 1 in patterns
                        and patterns[r - 1] == patterns[r + 1]
                        and patterns[r] != patterns[r - 1]
                    ):
                        findings.append(
                            Finding(
                                rule_id=self.id,
                                sheet=sheet_name,
                                ref=f"{col}{r}",
                                description="Formula is an outlier in its column.",
                                severity=self.severity,
                                risk=self.risk,
                            )
                        )
        return findings

    def fix(self, wb: WorkbookModel, finding: Finding) -> list[Edit]:
        sheet = wb.sheets[finding.sheet]
        c, r = _split_ref(finding.ref)

        cell_above = sheet.cells.get(f"{c}{r - 1}")
        if not cell_above or not cell_above.f:
            return []

        f_above = cell_above.f

        tokens = tokenize(f_above)
        out = []
        for t in tokens:
            if t.type == TokenType.OPERAND:
                val = t.value

                def repl(m):
                    col_part = m.group(1)
                    abs_row = m.group(2)
                    row_num = int(m.group(3))
                    if abs_row == "$":
                        return m.group(0)
                    new_row = max(1, row_num + 1)
                    return f"{col_part}{abs_row}{new_row}"

                val = re.sub(r"(?<![A-Za-z])([\$]?[A-Za-z]+)([\$]?)(\d+)\b", repl, val)
                out.append(val)
            else:
                out.append(t.value)
        new_f = "".join(out)

        return [
            CellEdit(
                op="SetFormula", sheet=finding.sheet, ref=finding.ref, formula=new_f
            )
        ]


registry.register(RuleR01())
registry.register(RuleR02())
registry.register(RuleR03())
registry.register(RuleR04())
registry.register(RuleR05())
registry.register(RuleR06())
registry.register(RuleR07())
registry.register(RuleR20())
registry.register(RuleR08())
