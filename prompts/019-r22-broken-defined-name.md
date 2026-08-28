# 019 — r22-broken-defined-name

## Goal
Implement Rule R22 (Broken defined name).

## Spec sections
> §4. Audit rules
> | R22 | Broken defined name | warning | safe | definition contains `#REF!` | delete the dead name |

## In scope / out of scope
- **In scope**: Implementing `RuleR22` in `backend/audit/rules_structure.py`. Extracting defined names in `backend/workbook/reader.py`. Modifying defined names in `backend/workbook/xml_patcher.py`. Adding `WorkbookEdit` to `backend/model.py` for workbook-level edits (or `DeleteDefinedName`).
- **Out of scope**: Implementing any other rules.

## Ponytail ladder
- Architecture:
  1. Update `WorkbookModel` in `backend/model.py` with `defined_names: dict[str, str]` (name to formula/reference).
  2. In `backend/workbook/reader.py`, parse `<definedNames>` from `workbook.xml` and populate `defined_names`.
  3. `RuleR22` detects if `#REF!` is in the defined name value.
  4. Fix: Needs a new `WorkbookEdit` in `backend/model.py` since defined names are workbook-level. `op="DeleteDefinedName", name=...`.
  5. In `backend/workbook/xml_patcher.py`, process `WorkbookEdit`s and modify `<definedNames>` in `workbook.xml`.

## Plan
1. Commit this prompt file.
2. Update `backend/model.py` to include `defined_names` in `WorkbookInventory` or `WorkbookModel` itself (let's add it to `WorkbookModel` if we use a separate class, or just `WorkbookModel` like `shared_strings`).
3. Update `backend/model.py` with `WorkbookEdit`. Add to `Edit = CellEdit | SheetEdit | WorkbookEdit`.
4. Update `backend/workbook/reader.py` to parse `<definedName>` nodes.
5. Update `backend/workbook/xml_patcher.py` to handle `DeleteDefinedName` inside `xl/workbook.xml`.
6. Implement `RuleR22` in `backend/audit/rules_structure.py`.
7. Write tests.
8. Ensure all tests and linters pass.

## Acceptance
- Defined names containing `#REF!` are detected and deleted correctly.
- All tests and linting pass.

## Rollback
Revert changes to models, readers, patchers, and rules.
