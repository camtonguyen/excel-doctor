# 022 — r07-empty-cell-breaks-chain

## Goal
Implement Rule R07 (Empty cell breaks a formula chain).

## Spec sections
> §4. Audit rules
> | R07 | Empty cell breaks a formula chain | warning | value | cell empty, cells above and below in the same column both have `<f>` | fill by translating the formula below up one row |

## In scope / out of scope
- **In scope**: Implementing `RuleR07` in `backend/audit/rules_formula.py`. Detecting empty cells surrounded by formula cells vertically. Synthesizing the formula by translating the formula from the cell below.
- **Out of scope**: Implementing any other rules.

## Ponytail ladder
- Architecture:
  1. `RuleR07` analyzes each column.
  2. If cell `col{r}` is missing/empty, but `col{r-1}` and `col{r+1}` both contain formulas (`f`), then flag `col{r}` as breaking a chain.
  3. The fix synthesizes a new formula for `col{r}` by parsing the formula in `col{r+1}` and translating all relative row references up by 1.

## Plan
1. Commit this prompt file.
2. Implement `RuleR07` in `backend/audit/rules_formula.py`.
3. Add a helper `translate_formula(f, row_offset)` (if not existing) to translate relative references, or simply write custom logic for `RuleR07`.
4. Add unit tests in `backend/tests/rules/test_rules_formula.py`.
5. Ensure tests and linters pass.

## Acceptance
- Empty cells between formula cells are flagged.
- The fixed formula is correctly translated up 1 row.
- All tests and linting pass.

## Rollback
Revert changes to rules_formula.py and its tests.
