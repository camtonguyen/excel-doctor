# 020 — r23-stray-empty-sheet

## Goal
Implement Rule R23 (Stray empty sheet).

## Spec sections
> §4. Audit rules
> | R23 | Stray empty sheet | style | safe | no cell has content and no sheet references it | propose deletion, unchecked by default |

## In scope / out of scope
- **In scope**: Implementing `RuleR23` in `backend/audit/rules_structure.py`. Checking all formulas in the workbook and defined names for references to the sheet. Adding `op="DeleteSheet"` to `SheetEdit` in `backend/model.py`. Implementing `DeleteSheet` in `backend/workbook/xml_patcher.py`.
- **Out of scope**: Implementing any other rules.

## Ponytail ladder
- Architecture:
  1. Update `backend/workbook/formula.py` with `is_sheet_referenced_in_formula(formula, sheet_name)` to safely check if a sheet name is used in an OPERAND token.
  2. Implement `RuleR23` in `backend/audit/rules_structure.py`:
     - Loop through `wb.sheets`.
     - Check if the sheet has any cells (i.e., `sheet.cells` is empty).
     - Check if the sheet name is referenced in any formula in any other sheet's `cell.f`, or in any `wb.defined_names` formula.
     - If both are true (no content, no references), flag it.
     - Propose `SheetEdit(op="DeleteSheet", sheet=...)`.
     - Set `auto_fixable=False` since it proposes deletion and is unchecked by default.
  3. Add `DeleteSheet` to `SheetEdit` ops in `backend/model.py`.
  4. In `backend/workbook/xml_patcher.py`, process `DeleteSheet`:
     - Delete sheet from `xl/workbook.xml` (`<sheet>`).
     - Remove the target XML file entirely from the zipped output.
     - Remove the `<Relationship>` from `xl/_rels/workbook.xml.rels`.
     - Remove the `<Override>` from `[Content_Types].xml`.
  5. Write tests and verify lint.

## Plan
1. Commit this prompt file.
2. Update `backend/workbook/formula.py`.
3. Update `backend/model.py` to add `DeleteSheet`.
4. Update `backend/workbook/xml_patcher.py`.
5. Implement `RuleR23` in `backend/audit/rules_structure.py`.
6. Add unit tests for R23 in `backend/tests/rules/test_rules_structure.py`.
7. Ensure tests and linters pass.

## Acceptance
- Stray empty sheets are detected and deletion is correctly processed without breaking the workbook structure.
- All tests and linting pass.

## Rollback
Revert changes to models, patchers, and rules.
