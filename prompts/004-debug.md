# Debug

A file comes back broken and it isn't obvious why. Use /diagnosing-bugs with the
xlsx-specific first moves below.

## Before you write anything

1. Copy this file to prompts/NNN-<slug>.md and fill in the sections.
2. Commit that file alone: `prompt: <slug>`.
3. Only then start.

## First moves — xlsx-specific

1. **Unzip both files** (original and broken) to temp dirs.
2. **Diff the zip entry lists.** Is anything missing? Is `calcChain.xml` still there when
   it shouldn't be? (Trap 5.)
3. **Diff the XML of the touched sheets.** Look for:
   - `<c>` elements with missing `s` attributes (style wrecked).
   - Shared-string indices that point past the end of `sharedStrings.xml`.
   - `<f>` elements that lost their formula or gained a stale `<v>`.
4. **Open in LibreOffice.** Does it show the error? If not, it's an Excel-specific issue
   (likely `calcChain` or an `x14` extension).
5. **Open in Excel.** Note the exact error dialog text — it tells you which XML part is
   broken.

## Diagnosis

- What exact operation produced the broken file? (Which `CellEdit`s?)
- Which XML part is malformed? (Use `xmllint --noout` on each part.)
- Is the root cause in `patch/`, `styles.py`, or `rename_sheet.py`?
- Is this a known trap? Check `docs/mind/brain/Gotchas.md` first.

## Fix

- Write a failing test that reproduces the break, using the broken file as a fixture.
- Fix the code. Test passes.
- Run the full suite + presentation diff on all fixtures.
- Add the trap to `Gotchas.md` if it's new.

## Commits
`fix: <what was broken, imperative, lowercase>`. Body: one line naming the root cause.
