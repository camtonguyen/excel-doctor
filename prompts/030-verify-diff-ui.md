# Verification Engine and Diff UI (Milestone 7)

Read `plans/prompt-plan-excel-doctor.md` §6 (verification), §6b (htmx frontend), and §8 (milestone 7).

## Before you write anything

1. Copy this file to `prompts/030-verify-diff-ui.md` and fill in the sections.
2. Commit that file alone: `prompt: 030-verify-diff-ui`.
3. Only then start.

## Spec sections

```
§6. Verification and the diff table
After patching, run this chain — if it fails, no download:
1. It reopens. Re-read the zip, parse every XML part.
2. Nothing went missing. Compare zip entry lists before and after. Only permitted absence is calcChain.xml.
3. It recalculates. Count error cells after <= count before.
4. Cell-by-cell diff. Read cached values before and after, emit DiffEntry.
5. Presentation diff. Verify formatting attributes differ only on cells touched by CellEdit.

§6b. Endpoint contract
- POST /fix/{job} -> _diff.html
- POST /fix/{job}/confirm -> _ready.html
- GET /download/{job} -> binary .xlsx
```

## Ponytail ladder
- Does this need to exist? Yes, Milestone 7 requires verification and diff flow before download.
- Is it already in the codebase? `backend/verify/` is currently empty (`.gitkeep`). `backend/app.py` needs `/fix/{job}`, `/fix/{job}/confirm`, `/download/{job}`.
- Does the stdlib / existing stack handle it? `zipfile`, `lxml`, `subprocess` (soffice), `FastAPI`, `Jinja2Templates`.

## How to build
- Red first: write tests in `backend/tests/verify/test_verify.py` and `backend/tests/web/test_fix.py`.
- Build `backend/verify/` (reopen, entry comparison, recalculation, presentation diff, and diff computation).
- Build endpoints in `backend/app.py` and templates in `backend/templates/partials/` (`_diff.html`, `_ready.html`).
- Ensure all tests pass, ruff clean, mypy clean.

## Before you say you're done
- Test verification failure blocks download and surfaces error.
- Test diff table renders correctly and groups by rule.
- Presentation diff caught any unauthorized style/dimension/merge mutations.
- Full test suite passes.
