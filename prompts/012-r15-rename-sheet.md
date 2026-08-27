# 012 — r15-rename-sheet

## Goal
Implement Rule 15 (Sheet name contains special characters) and expand the XML patcher to rename sheets and safely update all formula references across the workbook according to §5.3.

## Spec sections
> §4. Audit rules
> R15 | Sheet name contains special characters | error | safe | `[ ] : \ / ? *`, comma, period, apostrophe, leading/trailing space, length > 31 | rename + update every reference (§5.3)

> §5.3 Renaming a sheet
> Update all of these:
> 1. `xl/workbook.xml` → `<sheet name="…">`
> 2. `<definedName>` entries in `workbook.xml`
> 3. Every `<f>` in every `xl/worksheets/sheetN.xml`
> When substituting inside formulas, distinguish `'Sheet name'!` from `Sheetname!`, and never substitute inside a string literal. Use the tokenizer in `workbook/formula.py`. Never a raw `str.replace`.

## In scope / out of scope
- **In scope**: `RuleR15` in `backend/audit/rules_structure.py`. Expanding `backend/model.py` to support `SheetEdit`. Adding `rename_sheet_in_formula` to `backend/workbook/formula.py`. Expanding `xml_patcher.py` to handle sheet renaming globally (updating `workbook.xml` sheets, definedNames, and all formulas in `sheetN.xml`).
- **Out of scope**: Handling chart or pivot cache references (tier A inventory flags these anyway, but formula tokenizer will safely ignore or update valid operands).

## Ponytail ladder
- Does this need to exist? Yes, it's explicitly mandated by the build order for R15.
- Already in the codebase? No, we have formula tokenization but no reference updating logic, and no `SheetEdit`.
- Stdlib? Stdlib `re` used inside `formula.py` is enough.
- One line? Renaming a sheet is highly complex and requires structural updates.

## Plan
1. Commit this prompt file.
2. Modify `backend/model.py` to add `SheetEdit` and update `DiffEntry` / `Finding` models if necessary.
3. Modify `backend/workbook/formula.py` to add `rename_sheet_in_formula(formula, old_name, new_name)`.
4. Modify `backend/workbook/xml_patcher.py` to process `SheetEdit(op="RenameSheet")`.
5. Create `backend/audit/rules_structure.py` with `RuleR15` (detection & fix generating safe names).
6. Write tests in `test_formula.py`, `test_rules_structure.py`, and `test_xml_patcher.py`.

## Acceptance
- `RuleR15` correctly flags sheets with `[]:\/?*,' .` and length > 31.
- `RuleR15` generates safe, unique names.
- `rename_sheet_in_formula` uses the tokenizer and safely replaces exact sheet name matches in `OPERAND` tokens, avoiding substrings or string literals.
- `xml_patcher.py` successfully rewrites `workbook.xml` (both `<sheet>` and `<definedName>`) and all `sheetN.xml` formulas.
- All tests and ruff lint pass.

## Rollback
Delete `rules_structure.py`, `test_rules_structure.py`, and revert changes to `model.py`, `formula.py`, and `xml_patcher.py`.
