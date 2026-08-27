# Excel Doctor — Gotchas

Every trap hit during the build, with the file and line that proves it.
Entries from §9 of the spec are seeded below; new traps found mid-build go here
before the fix is committed.

---

## Trap 1: Google Sheets and Excel disagree about `""`

For `=A1+B1` where `B1` returns an empty string, Google produces a number and Excel
produces `#VALUE!`. A Google-exported file carries the "correct" cached value, so the
file looks fine until someone opens it in Excel. R04 exists for it.

**Source:** §9.1, verified against `fixtures/sokho_google.xlsx`.

---

## Trap 2: Google writes `#ERROR!` with `t="str"`

Google's error token is `#ERROR!` with `t="str"`, not `t="e"`. The error detector must
catch both shapes and distinguish a cell with a formula (computed error) from one without
(pasted literal).

**Source:** §9.2.

---

## Trap 3: JS libraries strip the leading `=` from formulas

Every regex anchored on `^=` will silently match nothing. Normalize to one shape at read
time.

**Source:** §9.3.

---

## Trap 4: LibreOffice doesn't implement all Excel functions

`XLOOKUP`, `FILTER`, `UNIQUE`, `SEQUENCE` won't evaluate. Post-2007 functions like
`TEXTJOIN`, `IFS`, `CONCAT` need an `_xlfn.` prefix in the XML. Verification must tell
"a real error" apart from "LibreOffice doesn't know this function".

**Source:** §9.4.

---

## Trap 5: Not deleting `calcChain.xml` corrupts the file

If any `<f>` is changed, `calcChain.xml` must be deleted and removed from
`[Content_Types].xml` and `workbook.xml.rels`. Leave it and Excel declares the file
corrupt with "Excel found unreadable content".

**Source:** §9.5.

---

## Trap 6: Shared formulas (`t="shared"`)

Only the first cell holds the real formula; the rest carry just an `si`. Editing the
first cell edits the whole group. Expand shared formulas into individual formulas before
editing any one of them.

**Source:** §9.6.

---

## Trap 7: The 1904 date system

Read `<workbookPr date1904="1"/>`. Ignore it and every date is off by four years.

**Source:** §9.7, verified against `fixtures/date1904.xlsx`.

---

## Trap 8: Sheet renaming must skip quoted strings

A sheet name can appear as data in a `SUMIF` criterion. Substituting there breaks the
logic. Use the formula tokenizer, never a raw `str.replace`.

**Source:** §9.8.

---

## Trap 9: `s` is a shared style index

Editing `cellXfs[i]` restyles every cell pointing at `i`. Always create a new `xf`
instead of mutating an existing one. See `ensure_xf` in `patch/styles.py`.

**Source:** §9.9.

---

## Trap 10: Header rows poison numFmt statistics

Many sheets carry a row numbering the columns `1, 2, 3…` right under the header.
Exclude the first 8 rows from numFmt statistics.

**Source:** §9.10.

---

## Trap 11: Empty cell mid-chain — bug or deliberate?

A machine can't tell. Always classify as `value`, show the consequence in the diff table,
let the user decide.

**Source:** §9.11.

---

## Trap 12: Some formula inconsistencies are intentional

Two different formulas in one column may mean someone changed the logic from a certain
row onward. Report it; don't auto-unify.

**Source:** §9.12.

---

## Trap 13: htmx swap destroys client state

A user ticks six groups, then filters the list, and loses everything if the fragment
gets swapped over. Keep tick state on the server keyed by `job_id`.

**Source:** §9.13.

---

## Trap 14: Missing `hx-encoding="multipart/form-data"`

Without it the file never arrives. htmx defaults to urlencoded.

**Source:** §9.14.

---

## Trap 15: Never download a binary through htmx

htmx takes the response and swaps it into the DOM, so xlsx contents spill as text. Use a
plain `<a href="/download/{job}">` with `hx-boost="false"`.

**Source:** §9.15.

---

## Trap 16: Long jobs must poll

Scanning a 200k-cell file takes 20 seconds. A synchronous `hx-post` hits a proxy timeout.
Return the `job_id` immediately and let the client poll.

**Source:** §9.16.

---

## Trap 17: 900 findings freezes the page

Paginate server-side from the start, not after discovering it with a real file.

**Source:** §9.17.
