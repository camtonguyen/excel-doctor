# Excel Doctor — Agent Foundation

This file is the single source of truth for every agent working on this project.
Claude Code reads it via `.claude/CLAUDE.md`; Codex and Antigravity read it natively.

## Spec

The full specification lives in `prompt-plan-excel-doctor.md` at the repo root.
Read the sections a prompt file names before starting — not the whole spec each turn.

## Shared Language

Read `CONTEXT.md` at the repo root before every session. It holds the project's
vocabulary so you don't re-derive terms or invent synonyms.

## Four Principles (§1)

These beat any argument about speed, elegance or convenience.

1. **Never overwrite the original.** Always emit a new file. The original is the control.
2. **Edit minimally.** Each fix touches exactly one cell or one attribute. Never
   "load the whole workbook and write it back" just to change five cells.
3. **Don't repair what you don't understand.** Hit an unfamiliar structure, skip it and
   record it in the report. Don't guess. A missed cell is an annoyance; a wrongly
   repaired cell costs money.
4. **Anything that changes a number needs its own approval.** Repairing a `#REF!` into a
   working reference will change an inventory balance. That is a business decision, not
   a technical one.

## Prompt-File Rule

**Before implementing anything, write a prompt file and commit it on its own.**
No prompt file, no code. The file goes in `prompts/` as `NNN-slug.md`.
See the spec §1b for the template.

## Keep Turns Short

- One slice per turn. A slice is one failing test, the code, the test passing — then stop.
- Read only the spec sections the prompt file names and the 2–3 files the slice touches.
- Report in three lines: what changed, tests green, next slice.
- Can't say the turn's goal in one sentence? It's too big — split the prompt file first.

## Git Rules

- Short trunk-based flow. `main` is always releasable.
- One change = one branch = one prompt file = one squashed commit on `main`.
- Branch off `main`: `git switch -c feat/<slug>`, `fix/<slug>`, `chore/<slug>`, etc.
- Commit subjects: `<area>: <imperative, lowercase, ≤72 chars>`.
- Rebase, don't merge. Keep the branch linear.
- **No `Co-Authored-By` trailer. No "Generated with" / tool-attribution footer. No emoji.**

## Deny Rules

These are load-bearing, not advisory — especially for auto-continuing agents.

- Never write to the uploaded file. Every patch targets a copy. (§1.1)
- Never modify a file under `fixtures/` — they are the test control. (§7)
- Never `git push --force`, never `commit --amend` on a shared branch, never commit to
  `main` directly.
- Never add a `Co-Authored-By` trailer or tool-attribution footer.
- Never delete `docs/mind/` or rewrite `CONTEXT.md` wholesale — append and edit in place.
- Stop and ask before any `git` operation that isn't `add`, `commit`, `switch -c`, or
  `status`/`diff`/`log`.

## Skills

Skills live in `skills/` at the repo root. Agent-specific dirs reference them via
symlink or config — never copy.

## Memory

The obsidian-mind vault lives at `docs/mind/`, tracked in the repo. Key notes:
- `brain/Gotchas.md` — every trap, with the file and line that proves it.
- `brain/Key Decisions.md` — ADR-shaped entries.
