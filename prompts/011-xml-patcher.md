# 011 — xml-patcher

## Goal
Implement the XML Patch engine (tier A) to safely apply CellEdits directly to an Excel zip package without corrupting it or dropping attributes.

## Spec sections
> §5.2 Tier A — patch the XML directly
> Flow: unzip to a temp dir → parse xl/worksheets/sheetN.xml with lxml → apply CellEdits → rewrite only the XML parts that changed → rezip, preserving the original entry order and compression level.
> Changing any `<f>` → delete `xl/calcChain.xml` and remove it from `[Content_Types].xml` and `workbook.xml.rels`.
> Changing `<f>` → also drop that cell's `<v>` so Excel recomputes on open.
> Set `<calcPr fullCalcOnLoad="1"/>` in `workbook.xml`.

## In scope / out of scope
- In scope: `xml_patcher.py` and applying SetValue, SetFormula, ClearCell edits. Preserving zip compression and order. Triggering recalculation via `fullCalcOnLoad` and removing `calcChain.xml`.
- Out of scope: SetNumFmt (§5.4 styling), Renaming sheets (§5.3), running the patch engine from the API.

## Ponytail ladder
- Does this need to exist? Yes, it's the core engine for fixing issues in Milestone 5.
- Is it already in the codebase? No, we only have model definitions and rule detection.
- Does the stdlib handle it? `zipfile` handles the archive, but `lxml` is needed for safe XML rewriting.
- Can it be one line? No, zip repackaging and XML rewriting with openpyxl constraints requires a dedicated module.

## Plan
1. Write this prompt file and commit.
2. Implement `xml_patcher.py` to parse sheet structures and rewrite zip.
3. Implement `test_xml_patcher.py` with integration tests checking all `op` types.
4. Verify tests pass.

## Acceptance
- Applies `SetValue` and modifies `<v>` without losing styles.
- Drops `calcChain.xml` if `<f>` is edited.
- Modifies `fullCalcOnLoad` in `workbook.xml`.
- Passes the test suite.

## Rollback
- Revert `xml_patcher.py` and `test_xml_patcher.py`.
