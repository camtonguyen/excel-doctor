# New Rule

For adding an audit rule R09. Use 000-implement.md for everything else.

## Before you write anything

1. Copy this file to prompts/NNN-<slug>.md and fill in the sections.
2. Commit that file alone: `prompt: <slug>`.
3. Only then start.

## The rule contract (§4)

Every rule is a class extending `Rule` with:
- `id`: "R09"
- `title`: "Số lưu dưới dạng văn bản"
- `why`: "SUM và SUMIF bỏ qua các ô này. Nhìn thì giống số nhưng không cộng được."
- `severity`: "warning"
- `risk`: "value"
- `auto_fixable`: True
- `detect(wb) -> list[Finding]`
- `fix(wb, finding) -> list[CellEdit]`

## Spec sections
| R09 | Number stored as text | warning | value | `t="s"`/`inlineStr` whose content parses as a number | coerce to numeric, auto-detecting thousands and decimal separators |

## Ponytail ladder
- Does this rule need to exist? Is it in the §4 table? Yes.
- Is it already in the codebase? Check `audit/rules_*.py`. No.
- Does the stdlib handle the detection? (`re`, `unicodedata`, etc.) Yes, `re` and float/int parsing with separator detection.
- Can the detect/fix be one function each? Yes.

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
