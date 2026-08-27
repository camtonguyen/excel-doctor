# Excel Doctor — Key Decisions

ADR-shaped entries for decisions that shaped the project.

---

## KD-001: Tier A (zipfile + lxml) over openpyxl as the primary editor

**Date:** 2026-08-27
**Status:** Accepted

**Context:** We need to edit xlsx files while preserving every presentational detail —
fonts, fills, borders, column widths, merges, charts, pivot tables, macros, images,
conditional formatting, and more. openpyxl is the standard Python xlsx library but it
drops content it doesn't model (charts partially, pivots partially, macros entirely,
threaded comments, sparklines, form controls, ActiveX).

**Decision:** Use `zipfile` + `lxml` (tier A) as the primary editing path. An xlsx file
is a zip of XML parts; we unzip, parse only the parts we need to edit with lxml, apply
changes, and rezip — preserving everything else byte-for-byte. openpyxl (tier B) is a
fallback for operations tier A can't handle cleanly.

**Consequences:**
- (+) Nothing is dropped — if we don't touch it, it survives.
- (+) We control exactly what changes, which makes the presentation diff reliable.
- (-) More manual work for each operation (must understand the XML schema).
- (-) Must handle calcChain, sharedStrings, styles manually (hence §5.2–5.4).

---

## KD-002: htmx over an SPA framework

**Date:** 2026-08-27
**Status:** Accepted

**Context:** The app has one page with five screens (upload → scanning → report → diff →
download). The real state lives on the server: the temp file, the scan result, the
approved fix list, the diff. An SPA would need to mirror this state on the client.

**Decision:** Use htmx 2.x. The server renders HTML fragments and state exists in exactly
one place. No build step, no bundle, no client state management. JavaScript is allowed in
exactly three places (drag-drop, filename display, beforeunload warning).

**Consequences:**
- (+) No build step, no client state, simpler mental model.
- (+) Each fragment is self-contained and testable without a browser.
- (-) Must handle polling, pagination, and state preservation server-side.
- (-) Three htmx-specific traps to avoid (traps 14, 15, 16 in Gotchas.md).

---

## KD-003: LibreOffice headless for verification

**Date:** 2026-08-27
**Status:** Accepted

**Context:** After patching, we need to verify that formulas recalculate correctly. Python
libraries can read cached values but can't recalculate — that requires an actual
spreadsheet engine.

**Decision:** Use `soffice --headless --convert-to xlsx` to recalculate formulas and
compare error counts before/after. Accept that LibreOffice doesn't implement all Excel
functions (trap 4) — the verification must distinguish "real error" from "LO doesn't know
this function".

**Consequences:**
- (+) Catches formula errors that survived patching.
- (+) No dependency on Excel itself.
- (-) LibreOffice is a heavy dependency for CI.
- (-) Must handle the function gap (XLOOKUP, FILTER, etc.) without false alarms.
