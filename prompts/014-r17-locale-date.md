# 014 — r17-locale-date

## Goal
Implement Rule R17 (Locale-ambiguous date format) to leverage the newly built style patcher engine.

## Spec sections
> §4. Audit rules
> | R17 | Locale-ambiguous date format | style | display | numFmt starts with `mm-dd` or `m/d/yy` | switch to `dd/mm/yyyy` |

## In scope / out of scope
- **In scope**: `backend/audit/rules_display.py` with `RuleR17`. Updating `backend/audit/__init__.py`.
- **Out of scope**: Implementing any other rules.

## Ponytail ladder
- Does this need to exist? Yes, it's a required rule.
- Already in the codebase? No.
- Stdlib? Use `str.startswith` for matching format prefixes.
- One line? Yes, simple regex or prefix match on `cell.num_fmt`.

## Plan
1. Commit this prompt file.
2. Create `backend/audit/rules_display.py`.
3. Implement `RuleR17`.
   - Iterate through sheets and cells.
   - If `cell.num_fmt` is set, normalize it (lowercase, strip brackets).
   - If it starts with `mm-dd` or `m/d/yy` (or similar, maybe use regex `^(mm?-dd?|m/d/yy)` to be safe), emit a `style` Finding.
   - The Finding includes a `CellEdit` with `op="SetNumFmt"` and `num_fmt_code="dd/mm/yyyy"`.
4. Import `rules_display` in `backend/audit/__init__.py`.
5. Write tests in `backend/tests/rules/test_rules_display.py`.

## Acceptance
- Ambiguous formats like `m/d/yyyy` or `mm-dd-yy` are flagged.
- Valid formats like `dd/mm/yyyy` or `yyyy-mm-dd` are ignored.
- The generated edit correctly targets `SetNumFmt`.
- All tests and ruff lint pass.

## Rollback
Delete `rules_display.py`, `test_rules_display.py`, revert `__init__.py`.
