# 005 — reader-inventory

## Goal
Implement the workbook reader skeleton and inventory scanner to detect xlsx features that mandate tier A patching (charts, pivots, macros, etc.).

## Spec sections
> §5.1 Choosing a tier
> Before patching, `inventory.py` opens the zip and reads `[Content_Types].xml` and `xl/_rels/`. If any of the following is present, **tier A is mandatory**, because openpyxl would drop it:
> - `xl/charts/`, `xl/drawings/`, `xl/media/` — charts and images
> - `xl/pivotCache/`, `xl/pivotTables/` — pivot tables and slicers
> - `xl/vbaProject.bin` — macros
> - `xl/threadedComments/`, `xl/persons/` — threaded comments
> - `xl/tables/` — ListObjects
> - external links under `xl/externalLinks/`
> - conditional formatting using the `x14` extension
> - sparklines, form controls, ActiveX

## In scope / out of scope
- **In scope**: `WorkbookInventory` model, `get_inventory` function inspecting the zip structure, testing with a mock xlsx builder, `reader.py` skeleton.
- **Out scope**: Actually parsing formulas or applying rules, building out the tier A patcher logic.

## Ponytail ladder
- Does this need to exist? Yes, §5.1 mandates detecting tier A features.
- Is it already in the codebase? No.
- Does the stdlib handle it? `zipfile` and `xml.etree.ElementTree` will handle checking paths and `[Content_Types].xml`.
- Can it be one line? No, multiple paths and XML relationships must be checked.

## Plan
1. Create `backend/model.py` for domain models.
2. Create test fixtures setup (`fixtures_meta.yaml` and a generator).
3. Write failing test for `inventory.py`.
4. Implement `inventory.py` logic.
5. Create `reader.py` skeleton.

## Acceptance
- Tests pass asserting the exact inventory counts and features for different fixture files.

## Rollback
Delete `backend/workbook/inventory.py` and `backend/workbook/reader.py`.
