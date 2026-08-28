# 016 — r19-inconsistent-fonts

## Goal
Implement Rule R19 (Inconsistent fonts) to leverage the style patcher engine.

## Spec sections
> §4. Audit rules
> | R19 | Inconsistent fonts | style | display | group (font name, size) workbook-wide, flag groups under 1% | apply the majority font |

## In scope / out of scope
- **In scope**: Modifying `backend/model.py`, `backend/workbook/reader.py`, `backend/workbook/xml_patcher.py`, `backend/workbook/styles.py` to support reading and writing fonts. Implementing `RuleR19` in `backend/audit/rules_display.py`.
- **Out of scope**: Handling rich text inside cells (just cell-level fonts).

## Ponytail ladder
- Does this need to exist? Yes, it's a required rule.
- Already in the codebase? No, we don't even parse `font_name` and `font_size` yet.
- Stdlib? Use `collections.Counter` for grouping and finding the majority font.
- Architecture: 
  1. `CellModel` needs `font_name` and `font_size`. 
  2. `reader.py` parses `<fonts>` in `styles.xml` and maps `s` index -> `xf.fontId` -> `font`. 
  3. `RuleR19` groups by `(font_name, font_size)`, finds the majority (the mode), then loops all cells. If `cell.font` is in a group < 1% of total cells, emit a finding. 
  4. The fix is a `CellEdit` with `op="SetFont"`, `font_name=majority_name`, `font_size=majority_size`.
  5. `xml_patcher.py` and `styles.py` support `SetFont` by implementing `ensure_font_xf(root, ns, base_xf_index, font_name, font_size)`.

## Plan
1. Commit this prompt file.
2. Update `CellModel` and `CellEdit` in `backend/model.py` with font properties.
3. Update `backend/workbook/reader.py` to parse `fonts` and `cell_xfs_font_ids` to populate cell font info.
4. Update `backend/workbook/styles.py` with `ensure_font_xf` to reuse or create a font element and `xf`.
5. Update `backend/workbook/xml_patcher.py` to process `SetFont`.
6. Implement `RuleR19` in `backend/audit/rules_display.py`.
7. Write tests in `backend/tests/rules/test_rules_display.py`.

## Acceptance
- Cells with minority fonts (< 1% of total) are flagged and replaced with the majority font.
- `styles.xml` correctly receives new font tags and xf tags if needed, deduplicating them.
- Tests and lint pass.

## Rollback
Revert all modifications to model, reader, patcher, styles, rules_display, and test_rules_display.
