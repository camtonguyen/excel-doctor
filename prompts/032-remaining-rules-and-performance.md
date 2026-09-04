# Remaining Rules and Performance (Milestone 9)

Read `plans/prompt-plan-excel-doctor.md` §4 (Audit rules R01–R05), §7 (Fixtures: huge.xlsx), §8 (Milestone 9), and §9 (Trap 16: Long jobs).

## Before you write anything

1. Copy this file to `prompts/032-remaining-rules-and-performance.md` and fill in the sections.
2. Commit that file alone: `prompt: 032-remaining-rules-and-performance`.
3. Only then start.

## Spec sections

```
§4. Audit rules
| R01 | Formula contains #REF! | error | value | #REF! substring inside <f> | infer the intended reference from neighbours in the same column, propose it, never auto-apply |
| R02 | Cell currently evaluates to an error | error | value | t="e", or <v> holds an error token | trace back to the root error cell in the dependency chain; report only |
| R03 | Error code pasted in as literal text | error | value | no <f>, string value matches #(REF!|VALUE!|N/A|NAME?|DIV/0!|NUM!|NULL!|ERROR!) | clear to empty or 0 depending on the column's type |
| R04 | Arithmetic directly on a cell that returns "" | error | display | formula is refs and +-*/ only, and one ref points at a cell whose formula contains "" | wrap each ref in N(); for * and / use IFERROR(...,0) |
| R05 | Reference to a sheet that doesn't exist | error | value | Sheet! token not in the sheet list | report only |

Requirement on why: Written for a warehouse accountant, not a developer.

§8. Milestone 9
| 9 | Remaining rules + performance | 200k-cell file scans in under 20 seconds |
```

## Ponytail ladder
- Does this need to exist? Yes, Milestone 9 completes remaining rule fix capabilities (R03, R04), adds Vietnamese accountant explanations for R01–R05, and verifies the 200k-cell scan performance requirement (< 20 seconds).
- Is it already in the codebase? Detection for R01–R05 exists, but R03 and R04 `fix()` methods are not implemented (raising NotImplementedError when applied via `/fix`), `ClearCell` in `xml_patcher.py` leaves stale `t` attributes on cleared cells, and a performance test validating a 200k-cell workbook scan is missing.
- Does the stdlib / existing stack handle it? `lxml`, `re`, existing formula tokenizer and `xml_patcher`.

## How to build
- Red first: write tests for R03 `fix()` and R04 `fix()` in `backend/tests/rules/test_rules_formula.py` and test patching in `backend/tests/patch/test_xml_patcher.py`.
- Write performance test in `backend/tests/test_performance.py` validating that scanning a 200,000-cell workbook across all 23 registered rules completes in under 20 seconds.
- Implement `RuleR03.fix`: returns `CellEdit(op="ClearCell", ...)` (or `SetValue` with 0 if column is numeric) to clear pasted literal errors.
- Ensure `ClearCell` in `backend/workbook/xml_patcher.py` strips `t` attribute from the cell node so empty cells don't retain invalid type indicators.
- Implement `RuleR04.fix`: returns `CellEdit(op="SetFormula", ...)` wrapping referenced empty-string cells in `N(...)` and division/multiplication in `IFERROR(..., 0)`.
- Update Vietnamese accountant-friendly `title` and `why` descriptions for R01–R05 in `backend/audit/rules_formula.py`.
- Ensure all tests pass, ruff clean, mypy clean.

## Before you say you're done
- Test that R03 fix clears literal error cells properly in patcher without breaking valid cell attributes.
- Test that R04 fix correctly updates formula operands to use `N()`.
- Test that 200k-cell scan benchmark runs in under 20 seconds.
- Full test suite, ruff lint, and mypy pass.
