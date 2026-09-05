# 033 — Idempotency and Verification Hardening

## Goal
Implement and verify idempotency testing across fixtures (second repair pass finds 0 issues), original-on-failure byte-for-byte return on abort, Trap 13 server-side tick state retention across filtering, and no-JS full-page fallback.

## Spec sections
- §6. Verification and the diff table (abort deletes patched file and returns original byte-for-byte)
- §6b. Frontend with htmx (no-JS full-page fallback: requests without HX-Request return full page)
- §7. Tests (The three tests that outrank the rest: Idempotency, Presentation invariance, Original-on-failure; Layer 5 Web tests)
- §9. Known traps (Trap 13: htmx swap destroys client state; keep tick state on server)
- §10. Definition of done ("A second repair pass finds nothing to fix.")

## In scope / out of scope
In scope:
- Fixture idempotency test suite (`backend/tests/test_idempotency.py`) verifying that fixing repairable fixtures and scanning a second time produces 0 findings.
- Original-on-failure abort behavior: when verification fails, ensure patched file is cleaned up, original file is preserved byte-for-byte, and download returns original.
- Server-side tick state in `store.py` / `app.py` so filtering findings via `/findings/{job_id}` retains checked rules and cells.
- Full page fallback for requests without `HX-Request` header.

Out of scope:
- New audit rules or rule algorithms (all R01–R23 are implemented).
- Modifying fixture files (fixtures remain strictly read-only controls).

## Ponytail ladder
- Does this need to exist? Yes, §7 explicitly marks Idempotency and Original-on-failure as "the tests that outrank the rest", and §6b/§9.13 mandate no-JS and state retention.
- Is it already in the codebase? Partial verification exists, but idempotency tests, byte-for-byte fallback on verification abort, server-side tick state across filter, and no-JS responses are missing.
- Does the stdlib / existing stack handle it? Yes, FastAPI Request headers (`request.headers.get("hx-request")`), existing `store.py`, `pytest`.

## Plan
1. Commit this prompt file alone.
2. Add idempotency tests in `backend/tests/test_idempotency.py`.
3. Add original-on-failure test and enforcement in verification / web layer.
4. Add Trap 13 tick state retention and test in `test_fix.py` / `test_scan.py`.
5. Add no-JS full-page fallback for endpoints and test in `test_scan.py`.
6. Run full test suite, ruff, mypy, and CI verification check.

## Acceptance
- `PYTHONPATH=. pytest -q backend/tests/` passes 100%.
- Idempotency test passes across repaired fixtures.
- Original file returned byte-for-byte on verification failure.
- Trap 13 test passes (filter does not drop user selections).
- No-JS test passes (`HX-Request` missing returns full HTML).
- `ruff check backend/` and `mypy backend/ --ignore-missing-imports` are completely clean.

## Rollback
`git checkout main && git branch -D feat/033-idempotency-and-verification-hardening`
