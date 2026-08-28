# 021 — r06-running-balance-chain

## Goal
Implement Rule R06 (Running-balance chain skips a row).

## Spec sections
> §4. Audit rules
> | R06 | Running-balance chain skips a row | warning | value | formula `=X{n}±…` where `X` is the cell's own column and `n ≠ row-1`; only in columns with ≥4 correctly linked cells | rewrite `n` to `row-1` |

## In scope / out of scope
- **In scope**: Implementing `RuleR06` in `backend/audit/rules_formula.py`. Parsing formula references to identify `X{n}` references in the cell's own column. Identifying chains of ≥4 correct linkages. Flagging deviations and applying a fix.
- **Out of scope**: Implementing any other rules.

## Ponytail ladder
- Architecture:
  1. `RuleR06` needs to analyze each column in each sheet.
  2. For each cell with a formula in the column, parse the formula to see if it references the cell above it (same column, `row - 1`). Wait, the rule says: "formula `=X{n}±…` where `X` is the cell's own column and `n ≠ row-1`; only in columns with ≥4 correctly linked cells".
  3. We first identify which columns have ≥4 cells that reference `row - 1` in their own column.
  4. For those columns, any cell that references the same column but `n ≠ row - 1` (and `n` is an integer row number) is flagged.
  5. The fix changes the reference from `X{n}` to `X{row-1}`.

## Plan
1. Commit this prompt file.
2. Implement `RuleR06` in `backend/audit/rules_formula.py`.
3. Add unit tests in `backend/tests/rules/test_rules_formula.py`.
4. Ensure tests and linters pass.

## Acceptance
- Running balance deviations are flagged and correctly fixed.
- All tests and linting pass.

## Rollback
Revert changes to rules_formula.py and its tests.
