# Architect

For a new module, a seam that feels wrong, or a periodic survey. Not for adding a rule —
use 003-new-rule.md.

## Start with the grilling
Run /grill-with-docs, not /grill-me. This project needs the domain-model half: the
vocabulary is dense and half of it is xlsx internals. The session should end with
CONTEXT.md updated and, if a real decision was made, an entry in
docs/mind/brain/Key Decisions.md.

Questions the grilling must not skip:
- What is the interface, in one sentence, and what does it hide?
- Who calls it? If the answer is "one place", why is it a module?
- What does it do when the input is malformed? §1.3 says skip and report, never guess.
- Can it change a cell the user didn't approve? If yes, how does the diff catch it?

## Then /codebase-design
Deep module, small interface, clean seam, testable through that interface. The existing
seams are worth matching:
- `audit/` produces `Finding`s and never mutates.
- `patch/` consumes `CellEdit`s and never decides.
- `verify/` reads two files and never repairs.
That separation is why the diff table can be trusted. A proposal that blurs it needs a
very good reason.

## Ponytail
Hardest here, because architecture is where over-building starts. Before any new module:
- Can this be a function in an existing module?
- Are we adding a plugin system for a set that will never exceed 25 rules?
- Are we abstracting over two cases that have nothing in common but shape?

## Periodic survey
Every few days, run /improve-codebase-architecture. It hands you candidates; it does not
untangle anything. Pick at most one, and put it through this prompt like any other change.

## Output
An updated CONTEXT.md, a decision record if a call was made, and a prompt file
(000-implement.md, filled in) for the work itself. Architecture that doesn't end in a
prompt file is a conversation, not a plan.
