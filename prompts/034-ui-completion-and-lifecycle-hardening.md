# 034 — UI Completion and Lifecycle Hardening

## Goal
Implement search and live filtering in the report UI, group the diff table by cause (rule ID) stating cell change counts per cause and total, add page unload warning during active jobs, and implement 1-hour TTL with automatic cleanup for jobs.

## Spec sections
- §6. Verification and the diff table (`_diff.html` shows this table before offering the download, grouped by cause, stating plainly how many cells changed value)
- §6b. Frontend with htmx:
  - Filter and search: `<input type="search" name="q" placeholder="Lọc theo sheet hoặc ô…" hx-get="/findings/{{ job }}" hx-trigger="keyup changed delay:300ms, search" hx-target="#findings" hx-swap="innerHTML">`
  - JavaScript allowed #3: "Warning before leaving the page while a job is running"
  - Lifecycle: `job_id` is a UUID bound to a temp directory, with a one-hour TTL and automatic cleanup.
- §7. Tests (Web integration tests for filtering, diff table grouped presentation, and job store cleanup)
- §9. Known traps (Trap 13: tick state retention; Trap 15: binary download not through htmx; Trap 16: long jobs poll)
- §10. Definition of done (Every cell whose value changed appears in the diff table with its cause)

## In scope / out of scope
In scope:
- Search filter input in `_report.html` allowing filtering by sheet or cell reference live as the user types, swapped into the findings container.
- Diff table grouping by cause in `_diff.html`, clearly separating changes by rule ID with summaries of cells changed per rule and total changes.
- Page unload warning (`beforeunload` handler) in `index.html` active when a job is scanning or fixing, disabled once ready or idle.
- Job store TTL expiry: track creation time on each job in `store.py`, prune jobs older than 1 hour (3600 seconds) along with their temp directory automatically on access or via explicit cleanup method.
- Unit and web integration tests covering search filtering, diff table grouping, and TTL cleanup in `store.py` and `app.py`.

Out of scope:
- Changes to audit rule detection or XML patching logic.
- Modifying fixture files (fixtures remain strictly read-only controls).

## Ponytail ladder
- Does this need to exist? Yes, §6 explicitly requires diff table grouped by cause, §6b requires search filter input and 3rd allowed JS snippet (beforeunload warning), and §6b specifies 1-hour TTL with automatic cleanup.
- Is it already in the codebase? Backend support for `q` search parameter on `/findings/{job_id}` exists, but the UI search input in `_report.html` is missing. The diff table currently renders a flat list rather than grouped by cause. `index.html` lacks the beforeunload warning. `store.py` does not track timestamps or purge expired jobs after 1 hour.
- Does the stdlib / existing stack handle it? Yes: Jinja2 `groupby`, Python `time.time()`, vanilla JS `beforeunload`, FastAPI/httpx.

## Plan
1. Commit this prompt file alone: `prompt: 034-ui-completion-and-lifecycle-hardening`.
2. Add TTL tracking and automatic expired job cleanup in `backend/store.py` with tests in `backend/tests/test_store.py`.
3. Add search input to `backend/templates/partials/_report.html` and ensure `/findings/{job_id}` query filtering interacts cleanly with template rendering.
4. Update `backend/templates/partials/_diff.html` to group diff entries by cause (rule ID) with headers, counts, and descriptions.
5. Add `beforeunload` warning handler in `backend/templates/index.html` when scanning/processing is active.
6. Add comprehensive web tests in `backend/tests/web/test_scan.py` and `backend/tests/web/test_fix.py`.
7. Verify all tests pass, ruff check clean, mypy clean, and CI prompt trailer check passes.

## Acceptance
- `backend/store.py` purges jobs older than 1 hour (3600s).
- `_report.html` contains the search filter input pointing to `/findings/{job}`.
- `_diff.html` renders diff entries grouped by rule cause with counts.
- `index.html` warns before unload if an operation is running.
- Full test suite passes: `PYTHONPATH=. pytest -q backend/tests/`.
- `ruff check backend/` and `mypy backend/ --ignore-missing-imports` are completely clean.

## Rollback
`git checkout main && git branch -D feat/034-ui-completion-and-lifecycle-hardening`
