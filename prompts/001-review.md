# Review

Run /code-review over the diff since this branch left main. Two axes, as parallel
sub-agents so neither contaminates the other, plus a third axis specific to this project.

## Axis 1 — Standards
Repo coding standards, plus a Fowler smell baseline. Also check, because this codebase
attracts them:
- Broad `except:` around zip or XML work, swallowing a corrupt-file signal.
- A raw `str.replace` anywhere near a formula. §5.3 forbids it — use the tokenizer.
- Mutating `cellXfs[i]` in place instead of calling `ensure_xf`. §5.4.
- A fix that writes a value where the spec says report-only.

## Axis 2 — Spec
Does the diff faithfully implement the prompt file it claims to? Read
prompts/NNN-<slug>.md and the spec sections it names. Flag scope that grew beyond
"In scope" as loudly as scope that fell short.

## Axis 3 — Blast radius
The one this project can't skip:
- Which cells can this change touch that the user did not approve?
- Does any code path write to the uploaded file rather than a copy?
- If verification fails midway, does the user get the original back, or a half-patched file?
- Does anything new get dropped from the zip on save?

Answer those four explicitly. "Not applicable" is an acceptable answer; silence is not.

## Ponytail pass
Re-run the ladder over the diff, not the plan. Look for: an abstraction with one caller,
a config option nobody sets, a dependency that replaces four lines of stdlib, a helper that
wraps a single call. Propose deletions with line numbers.

Do not propose simplifying §6, §6.5, §5.4 or §5.2. See the boundary in §1b.

## Output
A list, ordered by severity, each item naming a file and line. Then a verdict: ship, or
what has to change first. Do not fix anything in this pass — review and implementation in
one step means neither gets done properly.
