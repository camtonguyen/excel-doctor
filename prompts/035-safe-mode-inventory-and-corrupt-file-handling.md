# 035 — Safe Mode Inventory and Corrupt File Handling

## Goal
Surface Tier-A safe mode detection notice in the inspection slip report when workbooks contain charts, macros, or complex parts, and gracefully handle corrupt or unreadable files during scan polling with user-facing error reporting.

## Spec sections
- §5.1. Choosing a tier:
  "Before patching, inventory.py opens the zip and reads [Content_Types].xml and xl/_rels/. If any of the following is present, tier A is mandatory, because openpyxl would drop it:
  - xl/charts/, xl/drawings/, xl/media/ — charts and images
  - xl/pivotCache/, xl/pivotTables/ — pivot tables and slicers
  - xl/vbaProject.bin — macros
  - xl/threadedComments/, xl/persons/ — threaded comments
  - xl/tables/ — ListObjects
  - external links under xl/externalLinks/
  - conditional formatting using the x14 extension
  - sparklines, form controls, ActiveX
  Surface it in the report: 'File có biểu đồ và macro, đang dùng chế độ sửa an toàn.'"
- §7. Tests:
  "corrupt.xlsx: a broken file — must fail gracefully, never crash"
- §8. Build order:
  "Milestone 4: htmx page + _report.html | upload shows the inspection slip; filtering, pagination and CSV export work"

## In scope / out of scope
In scope:
- Run `get_inventory` during `background_scan` and store the inventory on the job.
- When workbook inventory requires Tier-A safe mode (charts, macros, pivot tables, drawings, etc.), display a notice/badge in `_report.html` informing the user that the file has complex features and safe patching mode is active.
- Detect scan failure due to corrupt or unreadable files (invalid zip, XML syntax errors) in `background_scan`, capture the error reason, and have `/scan/{job_id}` render `partials/_error.html` with an appropriate message and status code instead of falling through to an empty report.
- Web integration tests verifying safe mode banner display in `_report.html` when uploading workbooks with macros or charts (e.g. `chart_pivot.xlsx`, `macro.xlsm`).
- Web integration tests verifying corrupt or invalid file uploads cleanly result in error status and `_error.html` display.

Out of scope:
- Mutating fixtures (fixtures remain strictly read-only controls).
- Changing XML patcher low-level logic.

## Ponytail ladder
- Does this need to exist? Yes, §5.1 explicitly requires surfacing the Tier-A safe mode notice in the report, and §7 requires corrupt files to fail gracefully without crashing or presenting false clean reports.
- Is it already in the codebase? `get_inventory` exists in `backend/workbook/inventory.py` but is not wired into `background_scan` or `_report.html`. In `app.py`, `check_scan` incorrectly treats `job["status"] == "error"` by rendering `_report.html` with 0 findings.
- Does the stdlib / existing stack handle it? Yes: Jinja2 conditionals in `_report.html`, Python exceptions in `app.py`.

## Plan
1. Commit this prompt file alone: `prompt: 035-safe-mode-inventory-and-corrupt-file-handling`.
2. Wire `get_inventory` into `background_scan` in `backend/app.py` and pass `inventory` to `_report.html`.
3. Add the safe mode notice in `backend/templates/partials/_report.html` when `inventory` requires Tier-A.
4. Update `check_scan` in `backend/app.py` to handle `job["status"] == "error"` by rendering `partials/_error.html` with status code 400.
5. Add web tests for safe mode notice and corrupt file handling in `backend/tests/web/test_scan.py`.
6. Verify all tests pass, ruff check clean, mypy clean, and CI prompt trailer check passes.

## Acceptance
- Files with macros or charts (e.g., `chart_pivot.xlsx`, `macro.xlsm`) show the safe mode notice in `_report.html`.
- Corrupt/unreadable file uploads return `_error.html` upon polling completion instead of empty `_report.html`.
- Full test suite passes: `PYTHONPATH=. .venv/bin/pytest -q backend/tests/`.
- `ruff check backend/` and `mypy backend/ --ignore-missing-imports` are completely clean.

## Rollback
`git checkout main && git branch -D feat/035-safe-mode-inventory-and-corrupt-file-handling`
