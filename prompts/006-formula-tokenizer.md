# 006 — formula-tokenizer

## Goal
Implement a formula tokenizer that splits Excel formulas into references, strings, and functions to enable safe rewriting without modifying string literals.

## Spec sections
> §8. Build order
> | 2 | `formula.py` tokenizer | splits refs, strings and functions correctly; tested against formulas with Vietnamese sheet names and commas |

> §9. Known traps
> 3. **JS libraries strip the leading `=` from formulas.** Normalize to one shape at read time.
> 8. **Sheet renaming must skip quoted strings.** A sheet name can also appear as data in a `SUMIF` criterion. Substituting there breaks the logic.

> §5.3 Renaming a sheet
> When substituting inside formulas, distinguish `'Sheet name'!` (quoted) from `Sheetname!` (unquoted), and **never substitute inside a string literal** — in `SUMIF(A:A,"nl_MUỐI,",B:B)` the sheet-looking text is data, not a reference. Use the tokenizer in `workbook/formula.py`. Never a raw `str.replace`.

## In scope / out of scope
- **In scope**: Tokenizer implementation in `backend/workbook/formula.py`, tests for tokenizer covering Vietnamese characters, commas inside strings, quoted vs unquoted sheet names.
- **Out of scope**: Actual sheet renaming logic or formula rewriting logic (that comes later).

## Ponytail ladder
- Does this need to exist? Yes, §5.3 and §9 explicitly require a tokenizer to avoid data destruction.
- Is it already in the codebase? No.
- Does the stdlib handle it? Standard `re` handles lexical scanning, but the grammar rules must be custom written for Excel formulas.
- Can it be one line? No, tokenizing formulas requires multiple regex patterns or a state machine to correctly balance quotes and sheet boundaries.

## Plan
1. Define Token dataclass and Tokenizer class in `formula.py`.
2. Write tests covering string literals, Vietnamese sheet names, missing `=` prefix.
3. Implement `tokenize` function using regular expressions.
4. Verify tests pass and tokenizer is lossless when reconstructing the formula.

## Acceptance
- Reconstructing the tokens produces the exact original formula (lossless).
- Token type is `STRING` for `"nl_MUỐI,"`.
- Token type is `SHEET` for `'Báo cáo'!`.

## Rollback
Delete `backend/workbook/formula.py` and its tests.
