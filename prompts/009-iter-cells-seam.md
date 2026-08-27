# 009 — iter-cells-seam

## Goal
Give `WorkbookModel` a single cell-iteration seam so every `Rule.detect()` stops
duplicating the nested sheet/cell walk.

## Spec sections
> §4. Audit rules
> Every rule is a class extending `Rule`. R06-R23 are the same shape as R01-R05:
> walk every cell, test a predicate, emit a `Finding`.

## Context
Architecture review (2026-08-27) flagged R01-R05 in `rules_formula.py` as five
copies of the same `for sheet_name, sheet in wb.sheets.items(): for ref, cell in
sheet.cells.items()` loop. The spec plans R06-R23 in `rules_datatype.py`,
`rules_format.py`, `rules_structure.py` in the same shape — 18 more copies
without a seam.

## In scope / out of scope
- **In scope**: `WorkbookModel.iter_cells()` yielding `(sheet_name, ref, cell)`;
  rewrite R01-R05 to use it.
- **Out of scope**: R06-R23 themselves, the Job/dict cleanup and template
  cleanup also flagged by the review (separate prompt files).

## Ponytail ladder
- Does this need to exist? Yes — the duplication is already 5x and the spec
  commits to 18 more rules in the same shape.
- Already in the codebase? No, but it's a two-line flatten of an existing
  pattern, not new capability.
- Stdlib? N/A — this is domain iteration order, not a stdlib concern.
- One line? The method body is one line (a nested generator expression is
  harder to read than two `for` statements, so kept as a loop).

## Plan
1. Add `WorkbookModel.iter_cells()` in `backend/workbook/reader.py`.
2. Rewrite R01, R02, R03, R04, R05 in `backend/audit/rules_formula.py` to loop
   over `wb.iter_cells()` instead of the nested `sheets`/`cells` walk.
3. Add one test asserting `iter_cells()` visits every cell exactly once.

## Acceptance
- `backend/tests/rules/test_rules_formula.py` passes unchanged (same finding
  counts and refs for R01-R05 against `sokho_google.xlsx`).
- New `iter_cells` test passes.
- No rule file contains a nested `for sheet_name, sheet in wb.sheets.items():`
  loop anymore.

## Rollback
Revert `reader.py` and `rules_formula.py` to the nested-loop form; delete the
new test.
