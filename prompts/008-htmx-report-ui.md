# 008 — htmx-report-ui

## Goal
Implement Milestone 4: the frontend HTML, HTMX interactions, paginated finding display, and CSV export.

## Spec sections
- §2 Architecture (Frontend is htmx + Jinja2, one hand-written app.css)
- §6b Frontend with htmx (GET /findings/{job} -> _findings.html with filtering and pagination, GET /report/{job}.csv, form setup)
- §8 Build order: Milestone 4 | htmx page + _report.html | upload shows the inspection slip; filtering, pagination and CSV export work

## In scope / out of scope
In scope:
- `templates/index.html` full page layout.
- `static/app.css` for basic styling.
- `templates/partials/_findings.html` for rendering the paginated list of findings.
- `/findings/{job_id}` endpoint supporting `rule`, `q`, and `page` query params.
- `/report/{job_id}.csv` endpoint for CSV download.

Out of scope:
- The actual XML patching (Milestone 5).
- JavaScript beyond the 3 permitted lines in §6b.

## Ponytail ladder
- Does this need to exist? Yes, it's Milestone 4 in the spec.
- Is it already in the codebase? No, index.html and /findings are missing.
- Does the stdlib handle it? `csv` handles CSV generation. Jinja2 handles templates.
- Can it be one line? No.

## Plan
1. Create `templates/index.html` and `static/app.css` with the upload form.
2. Implement `/findings/{job_id}` endpoint and `_findings.html` template.
3. Add CSV export endpoint `/report/{job_id}.csv`.
4. Write web tests for the new endpoints.

## Acceptance
- `test_scan.py` updated to verify index page and CSV export.
- Paginated findings render as HTMX fragments correctly.

## Rollback
git revert of the commits made on this branch.
