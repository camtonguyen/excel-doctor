# New Rule

For adding an audit rule R12. Use 000-implement.md for everything else.

## Before you write anything

1. Copy this file to prompts/NNN-<slug>.md and fill in the sections.
2. Commit that file alone: `prompt: <slug>`.
3. Only then start.

## The rule contract (§4)

Every rule is a class extending `Rule` with:
- `id`: "R12"
- `title`: "Giá trị Boolean hoặc phần trăm lưu dưới dạng văn bản"
- `why`: "Excel không nhận diện được giá trị logic (TRUE/FALSE) hoặc tỷ lệ phần trăm (%), dẫn đến các phép tính và hàm điều kiện (như IF, SUM) bị sai lệch hoặc bỏ qua."
- `severity`: "warning"
- `risk`: "value"
- `auto_fixable`: True
- `detect(wb) -> list[Finding]`
- `fix(wb, finding) -> list[CellEdit]`

## Spec sections
| R12 | Boolean or percentage stored as text | warning | value | `"TRUE"`, `"12%"` | coerce to the matching type |

## Ponytail ladder
- Does this rule need to exist? Is it in the §4 table? Yes.
- Is it already in the codebase? Check `audit/rules_*.py`. No.
- Does the stdlib handle the detection? (`re`, `unicodedata`, etc.) Yes, `re` matching for booleans (TRUE/FALSE) and percentage strings.
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
