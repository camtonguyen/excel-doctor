# Implement

Read prompt-plan-excel-doctor.md §1 (principles) and the spec sections named below before
touching code. Then use the ponytail skill for every decision about what to build, and the
/implement skill for how to sequence it.

## Before you write anything

1. Copy this file to prompts/NNN-<slug>.md and fill in the sections.
2. Commit that file alone: `prompt: <slug>`.
3. Only then start.

If the goal isn't clear enough to fill in "Out of scope", stop and run /grill-with-docs
instead. Building the wrong thing correctly is the failure mode this rule exists for.

## Spec sections
<paste the constraint lines you are implementing, verbatim>

## Ponytail ladder
Answer all four in the prompt file before planning:
- Does this need to exist? If the spec doesn't require it, it doesn't.
- Is it already in the codebase? Search `workbook/`, `patch/`, `audit/base.py` first.
- Does the stdlib handle it? `zipfile`, `lxml`, `re`, `unicodedata`, `datetime` cover
  most of this project.
- Can it be one line?

Ponytail does NOT apply to: §6 verification, §6.5 presentation diff, §5.4 ensure_xf,
§5.2 shared-strings and calcChain handling. Those are data-loss prevention. Leave them
verbose.

## Keep it short
Context is a budget; don't blow it.
- One slice per turn. Do the slice, report, stop. Don't batch three to "save round-trips".
- Read only the spec sections named above and the 2–3 files the slice touches. Don't
  re-read the spec or grep the tree each turn — that's what CONTEXT.md is for.
- Report in three lines: what changed, tests green, next slice. No reasoning recap, no
  echoing unchanged files.
- Can't say the turn's goal in one sentence? It's too big. Split the prompt file (/to-tickets)
  before writing code. If a task is genuinely long, /handoff to a fresh session before the
  window fills, not after it degrades.

## How to build
- Drive /tdd. Red first, from a real fixture in fixtures/, never a synthesised workbook.
- One vertical slice per commit. A slice is: a failing test, the code, the test passing.
- Touch one module per commit. If a change needs `audit/` and `patch/` together, that is
  two commits and probably two slices.
- Run the full suite after each slice, not at the end.

## Before you say you're done
- Every §7 test for the touched rules passes.
- The idempotency test passes: repair twice, second run finds nothing.
- If you touched `patch/`, the presentation diff (§6.5) is clean on every fixture.
- Any new trap you hit is written into docs/mind/brain/Gotchas.md, in the same branch.
- New vocabulary is in CONTEXT.md.
- Run /code-review using prompts/001-review.md before opening the PR.

## Commits
`<area>: <imperative, lowercase, ≤72 chars>`. No co-author trailer. No tool attribution.
No body unless the diff doesn't explain the why.
