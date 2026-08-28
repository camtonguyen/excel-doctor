# 018 — r21-bloated-used-range

## Goal
Implement Rule R21 (Bloated used range).

## Spec sections
> §4. Audit rules
> | R21 | Bloated used range | style | safe | declared dimension far exceeds the last cell with content | shrink `<dimension>`, cut file size |

## In scope / out of scope
- **In scope**: Implementing `RuleR21` in `backend/audit/rules_structure.py`. Parsing `<dimension>` in `backend/workbook/reader.py`. Applying the shrink in `backend/workbook/xml_patcher.py`. Adding `SetDimension` to `SheetEdit`.
- **Out of scope**: Modifying other rules.

## Ponytail ladder
- Architecture:
  1. Add `dimension: str | None` to `SheetModel`.
  2. Parse `<dimension ref="...">` in `reader.py`.
  3. Detect: R21 iterates sheets. Find the actual max row/col from `cells`. Compare with the declared `dimension`.
     - How to define "far exceeds"? E.g., if declared max_row > actual max_row + 100, or declared max_col > actual max_col + 10, or empty cells > 1000? Let's use `declared area > 2 * actual area` and `declared area - actual area > 100` as a heuristic, or simply if `declared_max_row > actual_max_row + 100` or `declared_max_col > actual_max_col + 20`. Let's use: if max row/col declared is more than actual, it's bloated, but to avoid noise, require the difference in row > 100 or col > 10.
  4. Fix: Update `SheetEdit` to have `op="SetDimension"`, with `dimension="A1:..."`.
  5. Apply: In `xml_patcher.py`, when applying `SetDimension`, update the `ref` attribute of `<dimension>` in the sheet XML.

## Plan
1. Commit this prompt file.
2. Update `backend/model.py` to include `dimension` in `SheetModel` and `SetDimension` in `SheetEdit`.
3. Update `backend/workbook/reader.py` to extract `dimension`.
4. Update `backend/workbook/xml_patcher.py` to handle `SetDimension` operations.
5. Implement `RuleR21` in `backend/audit/rules_structure.py`.
6. Write tests in `backend/tests/rules/test_rules_structure.py`.
7. Ensure all tests and ruff lint pass.

## Acceptance
- Bloated used range is detected and shrunk correctly.
- Fix logic rewrites `<dimension>` tag in sheet XML.
- All tests and linters pass.

## Rollback
Revert all modifications to models, readers, patchers, and rules.
