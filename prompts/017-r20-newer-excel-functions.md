# 017 — r20-newer-excel-functions

## Goal
Implement Rule R20 (Functions only available in newer Excel).

## Spec sections
> §4. Audit rules
> | R20 | Functions only available in newer Excel | warning | safe | `XLOOKUP XMATCH FILTER UNIQUE SORTBY SEQUENCE LET LAMBDA TEXTJOIN IFS SWITCH MAXIFS MINIFS CONCAT` | warn only, suggest `INDEX/MATCH` |

## In scope / out of scope
- **In scope**: Implementing `RuleR20` in `backend/audit/rules_formula.py`. Writing tests in `backend/tests/rules/test_rules_formula.py`.
- **Out of scope**: Implementing any other rules.

## Ponytail ladder
- Does this need to exist? Yes, it's a required rule.
- Already in the codebase? No.
- Stdlib? Use `backend.workbook.formula.tokenize_formula` to safely parse functions out of the formula string (avoiding false positives inside strings).
- Architecture:
  1. Iterate over all cells.
  2. If a cell has a formula, tokenize it.
  3. Look for function tokens (like `XLOOKUP(`, `FILTER(`, etc.) matching the list of newer Excel functions.
  4. If found, emit a `warning` Finding with `risk="safe"`. The finding description should suggest `INDEX/MATCH` or other equivalents.
  5. The rule is NOT auto_fixable (warn only).

## Plan
1. Commit this prompt file.
2. Implement `RuleR20` in `backend/audit/rules_formula.py`.
3. Import `RuleR20` in `backend/audit/__init__.py` if needed.
4. Write tests in `backend/tests/rules/test_rules_formula.py`.
5. Ensure all tests and ruff lint pass.

## Acceptance
- Formulas with `XLOOKUP`, `FILTER`, `UNIQUE`, etc. are flagged.
- The rule is marked `auto_fixable = False`.
- Tests and lint pass.

## Rollback
Revert changes to `rules_formula.py` and `test_rules_formula.py`.
