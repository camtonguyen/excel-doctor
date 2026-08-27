# 013 — styles-patcher

## Goal
Implement safe cell styling modifications via `styles.py` (§5.4) and expand `xml_patcher.py` to handle `SetNumFmt` operations without corrupting sibling cell styles.

## Spec sections
> §5.4 Adding a number format without wrecking styles
> This is the easiest way to ruin a file's appearance. A cell's `s` points at `cellXfs[i]`, and an `xf` bundles font, fill, border, alignment *and* numFmt together. Changing numFmt by editing `cellXfs[i]` also restyles every other cell sharing index `i`.
> The correct approach:
> def ensure_xf(styles, base_xf_index, num_fmt_code) -> int:
>     1. find the numFmtId for the code; if absent, create a numFmt with id >= 164
>     2. clone cellXfs[base_xf_index] into a new xf, changing only numFmtId and setting applyNumberFormat="1"
>     3. if an identical xf already exists, return its index (keeps styles.xml from bloating)
>     4. append to cellXfs and return the new index

## In scope / out of scope
- **In scope**: `backend/workbook/styles.py` with `ensure_xf`. Updating `xml_patcher.py` to parse current `s="N"` values from targeted cells and update `xl/styles.xml`. Modifying `xml_patcher.py` to apply the updated `s="N"` attribute for `SetNumFmt` operations.
- **Out of scope**: Implementing any detection rules (R11, R16–R19) — those belong in a subsequent slice.

## Ponytail ladder
- Does this need to exist? Yes, required to apply display patches safely.
- Already in the codebase? No.
- Stdlib? Handled by `lxml`.
- One line? No, cloning XML nodes and deduplication requires dedicated logic.

## Plan
1. Commit this prompt file.
2. Implement `backend/workbook/styles.py` containing `ensure_xf(styles_root, base_xf_index, num_fmt_code)`.
3. Modify `backend/workbook/xml_patcher.py` to process `SetNumFmt`.
   - Before writing `xl/styles.xml`, scan `sheetN.xml` to find the original `s` attributes for cells targeted by `SetNumFmt`. (Can be done efficiently by reading the tree first, then mutating `styles.xml`, then writing back).
4. Write tests in `backend/tests/workbook/test_styles.py` to verify `ensure_xf`.
5. Update `backend/tests/workbook/test_xml_patcher.py` to verify `SetNumFmt` works and preserves sibling styles.

## Acceptance
- `ensure_xf` successfully creates or reuses `numFmtId`s.
- `ensure_xf` clones `xf` nodes properly and deduplicates identical configurations.
- `xml_patcher.py` updates the targeted cell's `s` attribute without mutating the original `xf` node.
- All tests and ruff lint pass.

## Rollback
Delete `styles.py`, `test_styles.py`, and revert changes to `xml_patcher.py`.
