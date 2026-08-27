# 010 — r14-whitespace

## Goal
Implement R14 (stray whitespace / invisible characters), the first rule of
Milestone 5's `safe` group, and fix the rule registry so newly added rule
modules actually run.

## Spec sections
> §4. Audit rules
> R14 | Stray whitespace and invisible characters | style | safe |
> `v != v.strip()`, `  ​ ‌ ﻿ ‎ ‏`, doubled spaces,
> non-NFC strings | trim, NBSP → space, drop invisibles, normalize to NFC

> §8. Build order
> Milestone 5 | `xml_patcher.py` + R14, R15 (the `safe` group) | patch applies

## Context
While starting Milestone 5, found `backend/audit/rules_formula.py` only
registers its rules because pytest happens to import it as a side effect of
collecting `test_rules_formula.py` in the same process. Importing
`backend.app` alone (i.e. running the real server) leaves `registry.get_all()`
empty — `/scan` would silently report zero findings on every real file. Adding
`rules_datatype.py` for R14 would hit the exact same trap. Root-caused: fix it
once in `backend/audit/__init__.py`, which every rule module already transits
through on import.

## In scope / out of scope
- **In scope**: `backend/audit/__init__.py` auto-discovering every
  `rules_*.py` module so registration always runs; `RuleR14` (detect + fix) in
  a new `backend/audit/rules_datatype.py`; a new mock fixture with whitespace
  defects; a `WorkbookModel.resolve_shared_string` seam shared by R03 and R14.
- **Out of scope**: `xml_patcher.py` itself (next slice — R14's `fix()` only
  needs to produce a `CellEdit`, not apply one), R15 (separate slice, rename
  is a much bigger operation per §5.3).

## Ponytail ladder
- Does this need to exist? Yes, it's the next rule in the build order.
- Already in the codebase? The `_clean` logic doesn't exist; the shared-string
  resolution pattern already exists in R03 and is reused here.
- Stdlib? `unicodedata.normalize("NFC", …)` and `str.replace`/`re.sub` cover
  everything the rule needs — no new dependency.
- One line? Detection is `_clean(text) != text` — one function serves both
  detect and fix, so there's only one place that defines "what counts as
  stray whitespace."

## Plan
1. Fix `backend/audit/__init__.py` to auto-import every `rules_*.py` module
   in the package (`pkgutil.iter_modules` + `importlib.import_module`) so
   `registry` is populated on package import, not by import-order luck or a
   hand-maintained list that the next rule file can forget to join.
2. Add a `whitespace.xlsx` mock fixture (leading/trailing spaces, doubled
   space, NBSP, zero-width space, and one clean control string) via
   `backend/tests/generate_mocks.py`.
3. Add `WorkbookModel.resolve_shared_string(cell)` in `reader.py` — the
   `t == "s"` → `int(cell.v)` → `shared_strings[idx]` lookup was duplicated in
   R03; give it one home and use it from both R03 and R14.
4. Add `backend/audit/rules_datatype.py` with `RuleR14`: `detect()` flags any
   shared-string cell where `_clean(text) != text`; `fix()` returns a
   `SetValue` `CellEdit` with the cleaned text.
5. Add `backend/tests/rules/test_rules_datatype.py` covering all four defect
   shapes and the clean-string negative case.
6. Add a regression test proving `import backend.app` alone populates the
   registry (guards the root-cause fix).

## Acceptance
- `RuleR14` detects all four whitespace defect shapes on `whitespace.xlsx`
  and does not flag the clean control cell.
- `RuleR14.fix()` returns the correctly cleaned text.
- A fresh `import backend.app` (no test importing rule modules first) shows
  `registry.get_all()` non-empty.
- Full suite green.

## Rollback
Delete `rules_datatype.py`, `whitespace.xlsx`, its generator function, and the
new tests; revert `backend/audit/__init__.py`.
