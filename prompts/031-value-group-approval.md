# Value Group Per-Cell Approval (Milestone 8)

Read `plans/prompt-plan-excel-doctor.md` §1 (Principle 4), §4 (Risk classes and rules), §6b (htmx frontend), and §8 (Milestone 8).

## Before you write anything

1. Copy this file to `prompts/031-value-group-approval.md` and fill in the sections.
2. Commit that file alone: `prompt: 031-value-group-approval`.
3. Only then start.

## Spec sections

```
§1. Four Principles
4. Anything that changes a number needs its own approval. Repairing a #REF! into
a working reference will change an inventory balance. That is a business decision, not
a technical one.

§4. Risk classes
- safe — fixing changes no value at all (stripping whitespace, unifying number formats).
- display — changes how a value is shown, not what is stored (serial number → date).
- value — changes a number. Approved per cell, unchecked by default.

§8. Milestone 8
| 8 | The value group, R06–R10 | unchecked by default, approved per cell |
```

## Ponytail ladder
- Does this need to exist? Yes, Milestone 8 requires value group fixes to be approved per cell rather than per whole rule group, unchecked by default.
- Is it already in the codebase? Rule-level checkboxes exist, but per-cell selection and filtering for value risk are not yet implemented in `_report.html`, `_findings.html`, and `POST /fix/{job}`.
- Does the stdlib / existing stack handle it? FastAPI form parsing (`request.form()`), Jinja2 templates, htmx fragment swapping.

## How to build
- Red first: write test in `backend/tests/web/test_fix.py` verifying that value findings require individual cell approval, unchecked by default, and unapproved cells are not fixed.
- Update `backend/templates/partials/_report.html` to display rule metadata (title, why explanation in Vietnamese, severity, risk) from the registry, distinguishing safe/display group checkboxes from value per-cell approval.
- Update `backend/templates/partials/_findings.html` to provide per-cell checkboxes for value findings, allowing selective cell approval.
- Update `POST /fix/{job_id}` in `backend/app.py` to enforce per-cell approval for value-risk findings (`risk == 'value'`), applying fixes only to individually selected cells.
- Ensure all tests pass, ruff check clean, mypy clean.

## Before you say you're done
- Test that value-risk findings are not fixed unless individual cell is approved.
- Test that selecting one value cell fixes only that cell and leaves other cells of the same rule untouched.
- Test that safe and display rules still support group-level approval.
- Full test suite, ruff lint, and mypy pass.
