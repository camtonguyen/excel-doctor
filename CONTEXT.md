# Excel Doctor — Shared Language

Read this before every session. It holds the project's vocabulary.

## Architecture

| Term | Meaning |
|---|---|
| **tier A** | The safe editing path: `zipfile` + `lxml`. Edits the xlsx XML directly inside the zip, preserving everything that isn't explicitly changed. Mandatory when the file contains charts, pivots, macros, or images. |
| **tier B** | The fallback path: `openpyxl`. Used only when tier A cannot handle the edit. Risks dropping content openpyxl doesn't model. |
| **the inspection slip** | The `_report.html` screen. Shows the audit results grouped by severity, with each rule's `why` in Vietnamese. The user picks which groups to fix from here. |
| **the presentation diff** | The §6.5 check. Extracts `(font, fill, border, numFmt, column width, row height, merges)` before and after patching. Any difference outside the `CellEdit` list is a fatal error — it means the patch wrecked formatting. |

## Data Model

| Term | Meaning |
|---|---|
| **`Finding`** | One detected issue: rule ID, sheet, cell reference, description, severity, risk. Output of `Rule.detect()`. Immutable. |
| **`CellEdit`** | One approved repair operation. Exactly one of: `SetValue`, `SetFormula`, `SetNumFmt`, `ClearCell`. Input to the patch engine. |
| **`FixPlan`** | A list of `CellEdit`s the user approved. Produced from the checkbox form on the inspection slip. |
| **`DiffEntry`** | One cell that changed value after patching: sheet, ref, before, after, cause (rule ID), note. Shown in the diff table. |

## xlsx Internals

| Term | Meaning |
|---|---|
| **`xf`** | An entry in `cellXfs` inside `xl/styles.xml`. Bundles font, fill, border, alignment, and numFmt into one style record. A cell's `s` attribute is an index into this array. |
| **`numFmt`** | Number format code (e.g., `dd/mm/yyyy`, `#,##0`). Built-in IDs are 0–163; custom IDs start at 164. |
| **`sharedStrings`** | `xl/sharedStrings.xml`. A lookup table of all string values. A `t="s"` cell stores an index into this table, not the string itself. Removing an entry shifts all indices — never remove, only add. |
| **`calcChain`** | `xl/calcChain.xml`. Lists the order Excel recalculates formulas. Must be **deleted** (not edited) whenever any `<f>` is changed, or Excel declares the file corrupt. |
| **`t` attribute** | The cell type: `s` = shared string, `str` = inline formula result, `inlineStr` = inline string with `<is><t>`, `b` = boolean, `e` = error, `n` or absent = number. |
| **`s` attribute** | The style index. Points at `cellXfs[s]`. Shared — editing `cellXfs[i]` restyles every cell with `s="i"`. Use `ensure_xf` to clone instead. |
| **`ensure_xf`** | The function in `patch/styles.py` that safely changes a cell's numFmt without wrecking other cells' styles. Clones the xf, changes only numFmtId, deduplicates, returns the new index. |

## Risk Classes

| Class | Meaning | UI Behaviour |
|---|---|---|
| **`safe`** | Fix changes no value at all (trim whitespace, unify formats). | Pre-checked in the fix form. |
| **`display`** | Changes how a value is shown, not what is stored (serial → date). | Pre-checked but highlighted. |
| **`value`** | **Changes a number.** Approved per cell, not per group. | Unchecked by default. Each cell shown individually. |

## Screens

| Name | Template | Purpose |
|---|---|---|
| Upload | `index.html` | Drop a file, submit. |
| Scanning | `_scanning.html` | Self-polling progress indicator. |
| Inspection slip | `_report.html` | Audit results grouped by rule. Checkboxes to select fixes. |
| Diff table | `_diff.html` | Cell-by-cell before/after comparison. The most important screen. |
| Ready | `_ready.html` | Download button + summary. |

## Rules

See §4 of `prompt-plan-excel-doctor.md` for the full table. Rule IDs: R01–R23.
Each rule has `id`, `title` (Vietnamese), `why` (Vietnamese, for an accountant),
`severity` (error/warning/style), `risk` (safe/display/value), and `auto_fixable`.
