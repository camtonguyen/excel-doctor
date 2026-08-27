# New Rule

For adding an audit rule R24+. Use 000-implement.md for everything else.

## Before you write anything

1. Copy this file to prompts/NNN-<slug>.md and fill in the sections.
2. Commit that file alone: `prompt: <slug>`.
3. Only then start.

## The rule contract (§4)

Every rule is a class extending `Rule` with:
- `id`: e.g. "R24"
- `title`: short, Vietnamese (user-facing)
- `why`: 1–2 sentences on the damage, Vietnamese, for a warehouse accountant
- `severity`: error | warning | style
- `risk`: safe | display | value
- `auto_fixable`: bool
- `detect(wb) -> list[Finding]`
- `fix(wb, finding) -> list[CellEdit]`

## Spec sections
<quote the rule's row from §4 and any referenced spec sections>

## Ponytail ladder
- Does this rule need to exist? Is it in the §4 table?
- Is it already in the codebase? Check `audit/rules_*.py`.
- Does the stdlib handle the detection? (`re`, `unicodedata`, etc.)
- Can the detect/fix be one function each?

## How to build
- Drive /tdd. Red first, from a **real fixture** in `fixtures/`.
- If no fixture exercises this defect, create one (a real xlsx, not synthesised) and add
  it to `fixtures_meta.yaml`.
- One commit: failing test. Second commit: rule code + test passing.
- Run the full suite after the rule is green.

## Before you say you're done
- The rule's detect test asserts the exact finding count from `fixtures_meta.yaml`.
- Apply fix, re-detect, assert zero.
- If `risk == "value"`: verify the fix is unchecked by default in the UI.
- If you touched `patch/`, presentation diff (§6.5) is clean.
- New trap → `docs/mind/brain/Gotchas.md`.
- New vocabulary → `CONTEXT.md`.
