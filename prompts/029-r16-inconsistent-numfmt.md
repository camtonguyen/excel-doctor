# New Rule

For adding an audit rule R16. Use 000-implement.md for everything else.

## Before you write anything

1. Copy this file to prompts/NNN-<slug>.md and fill in the sections.
2. Commit that file alone: `prompt: <slug>`.
3. Only then start.

## The rule contract (§4)

Every rule is a class extending `Rule` with:
- `id`: "R16"
- `title`: "Định dạng số không đồng nhất trong cùng một cột"
- `why`: "Trong cùng một cột, một vài ô có định dạng số khác biệt so với đa số các ô còn lại (ví dụ có 2 ô định dạng 0.00 trong cột 50 dòng định dạng #,##0), gây mất tính nhất quán và khó đọc."
- `severity`: "style"
- `risk`: "display"
- `auto_fixable`: True
- `detect(wb) -> list[Finding]`
- `fix(wb, finding) -> list[CellEdit]`

## Spec sections
| R16 | Inconsistent number format within a column | style | display | group numFmt per column, skipping the first 8 header rows; flag a minority group of ≤3 cells that is under 1/10 of the majority | apply the majority's numFmt |

## Ponytail ladder
- Does this rule need to exist? Is it in the §4 table? Yes.
- Is it already in the codebase? Check `audit/rules_*.py`. No.
- Does the stdlib handle the detection? (`re`, `unicodedata`, etc.) Yes, grouping cell num_fmt per column.
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
