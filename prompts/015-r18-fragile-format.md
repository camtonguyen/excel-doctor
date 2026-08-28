# 015 — r18-fragile-format

## Goal
Implement Rule R18 (Fragile format code) to leverage the style patcher engine.

## Spec sections
> §4. Audit rules
> | R18 | Fragile format code | style | display | numFmt contains `_)`, `\(`, `[$-409]`, `[Red]` with odd escaping | reduce to the equivalent standard code |

## In scope / out of scope
- **In scope**: `backend/audit/rules_display.py` with `RuleR18`. Updating `backend/audit/__init__.py`.
- **Out of scope**: Implementing any other rules.

## Ponytail ladder
- Does this need to exist? Yes, it's a required rule.
- Already in the codebase? No.
- Stdlib? Use `re` for matching format patterns.
- One line? A few regex substitutions on `cell.num_fmt`.

## Plan
1. Commit this prompt file.
2. Implement `RuleR18` in `backend/audit/rules_display.py`.
   - Iterate through sheets and cells.
   - If `cell.num_fmt` is set, check if it contains fragile sequences: `_)`, `\(`, `[$-409]`, `[Red]`.
   - If it does, emit a `style` Finding with a `CellEdit` setting `num_fmt_code` to a cleaned version (e.g. remove `[$-409]`, `[Red]`, and replace `_)` with ``, `\(` with `(`). Wait, the spec says "reduce to the equivalent standard code". We can just strip the weird parts.
3. Import `RuleR18` in `backend/audit/__init__.py` if it needs to be explicitly exported.
4. Write tests in `backend/tests/rules/test_rules_display.py`.

## Acceptance
- Formats containing `[$-409]`, `[Red]`, `_)`, `\(` are flagged.
- Cleaned formats correctly remove these sequences or replace them with standard equivalents.
- The generated edit correctly targets `SetNumFmt`.
- All tests and ruff lint pass.

## Rollback
Revert changes to `rules_display.py`, `test_rules_display.py`, `__init__.py`.
