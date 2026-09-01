# New Rule

For adding an audit rule R13. Use 000-implement.md for everything else.

## Before you write anything

1. Copy this file to prompts/NNN-<slug>.md and fill in the sections.
2. Commit that file alone: `prompt: <slug>`.
3. Only then start.

## The rule contract (§4)

Every rule is a class extending `Rule` with:
- `id`: "R13"
- `title`: "Giá trị phần trăm lưu sai tỷ lệ"
- `why`: "Ô được định dạng phần trăm (%) nhưng lưu giá trị số nguyên lớn hơn 1 (ví dụ nhập 10 thay vì 0.1, khiến Excel hiểu thành 1000%), gây sai lệch lớn khi tính toán."
- `severity`: "warning"
- `risk`: "value"
- `auto_fixable`: False
- `detect(wb) -> list[Finding]`
- `fix(wb, finding) -> list[CellEdit]`

## Spec sections
| R13 | Percentage stored at the wrong scale | warning | value | numFmt is `%` but the value is an integer > 1 | report only — too ambiguous to auto-fix |

## Ponytail ladder
- Does this rule need to exist? Is it in the §4 table? Yes.
- Is it already in the codebase? Check `audit/rules_*.py`. No.
- Does the stdlib handle the detection? (`re`, `unicodedata`, etc.) Yes, inspecting cell numeric value and percentage number format code.
- Can the detect/fix be one function each? Yes.

## How to build
- Drive /tdd. Red first, from a **real fixture** in `fixtures/`.
- If no fixture exercises this defect, create one (a real xlsx, not synthesised) and add
  it to `fixtures_meta.yaml`.
- One commit: failing test. Second commit: rule code + test passing.
- Run the full suite after the rule is green.

## Before you say you're done
- The rule's detect test asserts the exact finding count from `fixtures_meta.yaml`.
- If `risk == "value"`: verify the finding is surfaced with value risk.
- If you touched `patch/`, presentation diff (§6.5) is clean.
- New trap → `docs/mind/brain/Gotchas.md`.
- New vocabulary → `CONTEXT.md`.
