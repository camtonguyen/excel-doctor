# Prompt plan — Excel Doctor

> This spec is written to be handed straight to an AI coding agent (Claude Code or equivalent).
> Read all of it before writing the first line of code. **§9 Known traps** matters most —
> those are the places nearly every first build gets wrong.
>
> **Language note.** The spec is in English; the product's user-facing copy is in Vietnamese.
> Every `title` and `why` string shown to a user must be written in Vietnamese, for a
> warehouse accountant, not a developer. Keep the two apart: code and comments in English,
> UI copy in Vietnamese.

---

## §0. Kickoff prompt (paste this to the agent)

```
Build a web app called "Excel Doctor". A user uploads any .xlsx/.xlsm file. The app scans
the whole workbook for formula errors, data-type errors and formatting errors, shows a
report grouped by severity, lets the user pick which groups of issues to fix, and returns
the repaired file.

Hard constraint: the returned file must be identical to the original in every presentational
respect — fonts, sizes, fills, borders, column widths, row heights, merges, freeze panes,
conditional formatting, data validation, charts, images, pivot tables, VBA macros, sheet
order, defined names, print areas. Only cells in the user-approved fix list may change.
If you cannot guarantee that for some kind of content, refuse to repair the file and say
why. Never repair it and silently drop something.

Frontend is htmx: the server renders HTML fragments. No SPA, no build step. See §6b.

Working agreement, in force from the first commit (full detail in §1b):
- Before implementing anything, write a prompt file to prompts/ and commit it on its own.
  No prompt file, no code.
- The repo carries a root AGENTS.md (the shared foundation), skills/, and prompts/, with
  thin adapters for Claude Code (.claude/), Codex (.codex/), and Antigravity (.agents/).
- Use mattpocock/skills for the process and the ponytail skill for restraint.
- Persistent memory lives in an obsidian-mind vault under docs/mind/.
- Short git flow. Short commit subjects. No co-author trailer, no tool attribution.
- Keep tasks and turns short: one slice per turn, split the prompt file rather than the
  session, don't waste context re-reading. See §1b.

Read the full spec in this file before starting. Build in the milestone order in §8.
After each milestone, run the tests in §7 and report results before moving on.
```

---

## §1. Non-negotiable principles

These four beat any argument about speed, elegance or convenience.

1. **Never overwrite the original.** Always emit a new file. The original is the control.
2. **Edit minimally.** Each fix touches exactly one cell or one attribute. Never
   "load the whole workbook and write it back" just to change five cells.
3. **Don't repair what you don't understand.** Hit an unfamiliar structure, skip it and
   record it in the report. Don't guess. A missed cell is an annoyance; a wrongly
   repaired cell costs money.
4. **Anything that changes a number needs its own approval.** Repairing a `#REF!` into a
   working reference will change an inventory balance. That is a business decision, not
   a technical one.

---

## §1b. Working agreement

### Three external pieces, three different jobs

| Piece | Job here | Install |
|---|---|---|
| [mattpocock/skills](https://github.com/mattpocock/skills) | the process: grilling, spec, tickets, TDD, code review, architecture survey | `npx skills@latest add mattpocock/skills`, then `/setup-matt-pocock-skills` once |
| [ponytail](https://github.com/DietrichGebert/ponytail) | restraint: refuse to build what doesn't need to exist | `npx skills add DietrichGebert/ponytail` |
| [obsidian-mind](https://github.com/breferrari/obsidian-mind) | memory: what we learned about xlsx internals survives the session | `shardmind install github:breferrari/obsidian-mind` into `docs/mind/` |

Install the skills through `npx skills`, not the Claude Code plugin. This project needs to
edit the skill files — the plugin ships them read-only.

### Ponytail's boundary in this project

Ponytail's ladder — does this need to exist, is it already in the codebase, does the
standard library do it, can it be one line — applies to every rule, every route, every
template. It does **not** apply to:

- the verification chain in §6, including every abort path
- the presentation diff in §6.5
- `ensure_xf` in §5.4, which is verbose for a reason
- the shared-strings and `calcChain` handling in §5.2

Ponytail itself excludes data-loss prevention from its minimalism rules, and §1 of this
spec *is* data-loss prevention. If the agent proposes collapsing one of those, that is
ponytail being applied outside its own stated boundary. Push back.

Everywhere else, prefer the boring answer. A rule that is a regex and a comparison does not
need a strategy class.

### Keep tasks and turns short

Context is a budget. A task that runs long enough to fill the window loses the start of its
own plan, and the agent begins re-deriving decisions it already made. Guard against it:

- **One slice per turn.** A slice is one failing test, the code, the test passing — then
  stop and report. Don't chain three rules in a single run "to save round-trips"; the
  round-trips are cheaper than a blown context.
- **Split the prompt file, not the session.** If a change won't fit in one short branch,
  it's two prompt files. `/to-tickets` exists for exactly this — break the plan into
  tracer-bullet tickets before starting, not halfway through when you're already deep.
- **Read narrow.** Open the spec sections the prompt file names and the two or three files
  the slice touches. Don't re-read the whole spec or `grep` the tree each turn — that's what
  `CONTEXT.md` and the prompt file are for.
- **Report short.** After a slice: what changed, tests green, next slice. Not a recap of the
  reasoning — the diff and the prompt file already hold it. No echoing files back that
  didn't change.
- **Hand off before you're full, not after.** When a task is genuinely long, run `/handoff`
  to compact into a fresh session rather than pushing the window to its limit and degrading.

The rule of thumb: if you can't state what this turn will do in one sentence, the turn is
too big — narrow it before writing code.

### The prompt-file rule

**Before implementing anything, write a prompt file and commit it on its own.** No prompt
file, no code. The file goes in `prompts/` as `NNN-slug.md` and contains:

```markdown
# NNN — <what this changes>

## Goal
One sentence. What is true after this that isn't true now.

## Spec sections
Which parts of prompt-plan-excel-doctor.md this implements. Quote the constraint lines.

## In scope / out of scope
Two lists. The second one is the important one.

## Ponytail ladder
- Does this need to exist? …
- Is it already in the codebase? …
- Does the stdlib handle it? …
- Can it be one line? …

## Plan
Numbered steps, each one a commit.

## Acceptance
How we know it's done. Name the tests.

## Rollback
What to revert if this turns out wrong.
```

Keep the prompt file itself short — one screen, not an essay. If it won't fit on a screen,
the change is too big and wants splitting with `/to-tickets`. The file exists to align, not
to document.

The point is not ceremony. It is that a prompt file makes the misalignment visible before
the code exists, which is the whole premise of `/grill-with-docs`. It also gives every
commit and PR something to point at.

### Agent config layout (Claude Code, Codex, Antigravity)

One portable foundation, three thin adapters. The rules that don't change between agents
live once, at the repo root, in `AGENTS.md` — the file all three read. Everything
agent-specific is an adapter that points back at it.

```
excel-doctor/
├── AGENTS.md               # THE foundation — read by Codex and Antigravity natively,
│                           # and by Claude Code via the pointer in CLAUDE.md.
│                           # Holds: the four §1 principles, the prompt-file rule,
│                           # the git rules, deny rules, where CONTEXT.md and the spec live.
├── CLAUDE.md               # one line: "Read AGENTS.md." Nothing else.
├── GEMINI.md               # Antigravity-only overrides, if ever needed. Empty to start.
│
├── skills/                 # canonical skill sources, installed by `npx skills`
│   ├── ponytail/           #   from DietrichGebert/ponytail
│   ├── grill-with-docs/    #   from mattpocock/skills
│   ├── to-spec/  to-tickets/  implement/  tdd/  code-review/
│   ├── codebase-design/  diagnosing-bugs/  improve-codebase-architecture/  handoff/
│   └── xlsx-internals/     #   ours — see below
│
├── prompts/                # the prompt files, agent-agnostic plain markdown
│   ├── 000-implement.md    #   the defaults, §1b
│   ├── 001-review.md
│   ├── 002-architect.md
│   ├── 003-new-rule.md
│   ├── 004-debug.md
│   └── …                   #   one per change, numbered as we go
│
├── .claude/                # Claude Code adapter
│   ├── skills/  → ../skills # symlink; Claude Code reads .claude/skills/
│   └── settings.json       # hooks (commit-msg guard lives in git, not here)
│
├── .codex/                 # Codex adapter
│   └── config.toml         # points skills + prompts dirs at ../skills, ../prompts
│
└── .agents/                # Antigravity adapter (default dir since v1.20.5)
    ├── rules/
    │   └── 000-foundation.md  # one Always-On rule: "@/AGENTS.md" — pulls in the foundation
    ├── skills/  → ../skills   # symlink
    └── workflows/
        ├── implement.md       # wraps prompts/000-implement.md as an Antigravity workflow
        ├── review.md          #   wraps prompts/001-review.md
        └── architect.md       #   wraps prompts/002-architect.md
```

Why this shape rather than three copies:

- **`AGENTS.md` is the one source of truth.** Codex reads it natively; Antigravity reads it
  natively (after `GEMINI.md`); Claude Code reaches it because `CLAUDE.md` says to. Write a
  rule once, all three obey it. Three separate manuals drift within a week.
- **`skills/` and `prompts/` are plain markdown with no agent SDK**, so every agent uses the
  same files. The per-agent dirs only *reference* them (symlink or config), never copy them.
- **Antigravity needs the rule to be inside `.agents/rules/`** to auto-apply it, so
  `000-foundation.md` is a one-line `@/AGENTS.md` include rather than a second copy. Keep
  each `.agents/rules/` file under the 12,000-character limit — the foundation include is
  tiny, so this only matters if you later split rules by topic.
- **Antigravity runs long chains without pausing** (auto-continue). That makes the deny
  rules in `AGENTS.md` load-bearing, not advisory — see below.

`AGENTS.md` is short. It states: the four principles from §1, the prompt-file rule, the git
rules, the deny rules, where `CONTEXT.md` lives, and a pointer to this spec. Nothing else —
the skills hold the process, `CONTEXT.md` holds the vocabulary, this spec holds the design.
An `AGENTS.md` that repeats them goes stale in three days.

**Deny rules (in `AGENTS.md`, enforced for every agent).** These matter most for Antigravity
and Codex non-interactive runs, which can edit many files before pausing:

- Never write to the uploaded file. Every patch targets a copy. (§1.1)
- Never modify a file under `fixtures/` — they are the test control. (§7)
- Never `git push --force`, never `commit --amend` on a shared branch, never commit to
  `main` directly. (git flow, below)
- Never add a `Co-Authored-By` trailer or tool-attribution footer. (git flow)
- Never delete `docs/mind/` or rewrite `CONTEXT.md` wholesale — append and edit in place.
- Stop and ask before any `git` operation that isn't `add`, `commit`, `switch -c`, or
  `status`/`diff`/`log`.

**Codex specifics.** Codex reads `AGENTS.md` at the root natively. Install the skills with
`npx skills@latest add mattpocock/skills` and `npx skills add DietrichGebert/ponytail`,
choosing Codex as a target; the installer writes the Codex-side config. Slash commands
become plain prompts — type `implement` (referring to `prompts/000-implement.md`) without a
leading `/`. Run non-interactively with `codex exec` only inside a branch, never on `main`.

**Antigravity specifics.** Point it at the workspace and it reads `GEMINI.md` then
`AGENTS.md`, then anything in `.agents/rules/`. The three workflows in `.agents/workflows/`
are the Antigravity front door to the same prompt files: `implement.md` loads
`prompts/000-implement.md`, walks the ponytail ladder, then drives the build. Register the
skills the same way (`npx skills … `, target Antigravity), which populates `.agents/skills/`.
Keep custom subagents, if any, in `.agents/agents/` with the documented YAML frontmatter.

**`skills/xlsx-internals/`** is the one skill we write ourselves. It is §5 and §9 of this
spec turned into a model-invoked skill, so any agent reaches for it automatically whenever
it touches `patch/`. Write it after milestone 5, once the traps are proven rather than
assumed.

### Memory: obsidian-mind

The vault lives at `docs/mind/`, tracked in the same repo. Three notes carry the weight:

- **`brain/Gotchas.md`** — every trap in §9 goes in here as its own entry, with the file and
  line that proves it. When a new one is found mid-build, it is added before the fix is
  committed. This note is the reason the second engineer on this project doesn't rediscover
  that `calcChain.xml` breaks Excel.
- **`brain/Key Decisions.md`** — one entry per ADR-shaped call: why tier A over openpyxl,
  why htmx over an SPA, why LibreOffice for verification.
- **`CONTEXT.md`** at the repo root — the shared language. This project has a lot of jargon
  and most of it is not English: `xf`, `numFmt`, `sharedStrings`, `calcChain`, tier A/B,
  `CellEdit`, the three `risk` classes, "the presentation diff", "the inspection slip".
  Build it during the first grilling session and keep it current. Without it the agent
  writes "the number formatting style index thing" for the rest of the project.

obsidian-mind ships hook configs for Claude Code, Codex (`.codex/hooks.json`) and Gemini
CLI (`.gemini/settings.json`). Antigravity reads the same `GEMINI.md` and `~/.gemini`
surface as Gemini CLI, so the vault's session hooks and `/om-*` commands carry over without
a fourth config; only the workspace-level `.agents/rules/000-foundation.md` include is
Antigravity-specific. Run `/om-wrap-up` at the end of a session and `/om-weekly` when a
milestone closes.

### Git flow

Short trunk-based flow. `main` is always releasable; all work happens on short-lived
branches that live one to three days and squash-merge back. No `develop`, no release
branches, no long-running forks. Every agent — Claude Code, Codex, Antigravity — follows
the same flow; the deny rules in `AGENTS.md` stop an auto-continuing agent from committing
straight to `main`.

```
main ─────●────────────●────────────●──────────────▶  (always green, always releasable)
          │            │            │
          │   squash   │   squash   │   squash
          ▼            ▼            ▼
   feat/r04-empty-  fix/calcchain-  feat/r15-sheet-
   string-guard     drop-on-write   rename           (1–3 days each)
```

**One change = one branch = one prompt file = one squashed commit on `main`.**

The loop, every time:

1. **Branch.** `git switch -c feat/<slug>` off the latest `main`. The slug matches the
   prompt file: `feat/r04-empty-string-guard`. Prefixes: `feat/`, `fix/`, `chore/`,
   `docs/`, `test/`.
2. **Prompt first.** Copy `prompts/000-implement.md` (or `002`, or `003`) to
   `prompts/NNN-<slug>.md`, fill it in, and commit it *alone*:
   `prompt: guard arithmetic on ""`. This is always the branch's first commit.
3. **Build in slices.** One vertical TDD slice per commit — failing test, code, green.
   Subject line: `<area>: <imperative, lowercase, ≤72 chars>`, where `<area>` is a
   directory name (`audit`, `patch`, `verify`, `workbook`, `templates`, `tests`, `docs`).
   Body only when the *why* isn't obvious from the diff; most commits have none.
4. **Rebase, don't merge.** Keep the branch current with `git rebase main`, never
   `git merge main` into it. The branch history stays linear so the squash is clean.
   Only rebase a branch nobody else has fetched.
5. **Review.** Run `/code-review` against `prompts/001-review.md` before opening the PR.
6. **PR.** Title = the prompt file's title. Body = a link to the prompt file plus a
   one-line summary of the diff. Nothing else — the prompt file already says why.
7. **Squash-merge** to `main`, then delete the branch. One commit lands per change, so
   `main`'s history reads as a list of changes, each pointing at its prompt file.

Hard rules, enforced not just remembered:

- **No `Co-Authored-By` trailer. No "Generated with" / tool-attribution footer. No emoji.**
  The history records what changed, not who or what typed it.
- Never commit to `main` directly. Never `git push --force` a shared branch. Never
  `git commit --amend` a commit that's already been pushed and fetched.
- `main` must stay green: a branch doesn't merge until §7's suite and the §6 verification
  pass on it.

Two hooks make the rules mechanical rather than aspirational:

```bash
# .git/hooks/commit-msg — reject banned trailers
grep -qiE '(^co-authored-by|generated with|🤖|noreply@anthropic)' "$1" && {
  echo "commit message contains a banned trailer or attribution"; exit 1; }
exit 0
```

```bash
# .git/hooks/pre-commit — no direct commits to main
[ "$(git symbolic-ref --short HEAD)" = "main" ] && {
  echo "commit to a branch, not main"; exit 1; }
exit 0
```

Install both on clone (a `chore:` commit adding a `scripts/install-hooks.sh` that copies
them into `.git/hooks/` is the first non-prompt commit in the repo). `.git/hooks/` isn't
version-controlled, so the script is how every machine and every agent gets the same guard.

### The five default prompts

These live in `prompts/` from day one and are copied, not edited, for each change.
They exist so that `implement`, `review` and `architect` mean the same thing every time.

| File | Invoke when | Drives |
|---|---|---|
| `000-implement.md` | building anything from the spec | `/implement` → `/tdd` → `/code-review`, under ponytail |
| `001-review.md` | before opening a PR | `/code-review`, two axes, plus this spec's own constraints |
| `002-architect.md` | a new module, or a seam that feels wrong | `/grill-with-docs` → `/codebase-design`, updates `CONTEXT.md` |
| `003-new-rule.md` | adding an audit rule R24+ | `/tdd` from a real fixture, under §4's rule contract |
| `004-debug.md` | a file comes back broken and it isn't obvious why | `/diagnosing-bugs`, with the xlsx-specific first moves |

Full text for the first three:

---

#### `prompts/000-implement.md`

````markdown
# Implement

Read prompt-plan-excel-doctor.md §1 (principles) and the spec sections named below before
touching code. Then use the ponytail skill for every decision about what to build, and the
/implement skill for how to sequence it.

## Before you write anything

1. Copy this file to prompts/NNN-<slug>.md and fill in the sections.
2. Commit that file alone: `prompt: <slug>`.
3. Only then start.

If the goal isn't clear enough to fill in "Out of scope", stop and run /grill-with-docs
instead. Building the wrong thing correctly is the failure mode this rule exists for.

## Spec sections
<paste the constraint lines you are implementing, verbatim>

## Ponytail ladder
Answer all four in the prompt file before planning:
- Does this need to exist? If the spec doesn't require it, it doesn't.
- Is it already in the codebase? Search `workbook/`, `patch/`, `audit/base.py` first.
- Does the stdlib handle it? `zipfile`, `lxml`, `re`, `unicodedata`, `datetime` cover
  most of this project.
- Can it be one line?

Ponytail does NOT apply to: §6 verification, §6.5 presentation diff, §5.4 ensure_xf,
§5.2 shared-strings and calcChain handling. Those are data-loss prevention. Leave them
verbose.

## Keep it short
Context is a budget; don't blow it.
- One slice per turn. Do the slice, report, stop. Don't batch three to "save round-trips".
- Read only the spec sections named above and the 2–3 files the slice touches. Don't
  re-read the spec or grep the tree each turn — that's what CONTEXT.md is for.
- Report in three lines: what changed, tests green, next slice. No reasoning recap, no
  echoing unchanged files.
- Can't say the turn's goal in one sentence? It's too big. Split the prompt file (/to-tickets)
  before writing code. If a task is genuinely long, /handoff to a fresh session before the
  window fills, not after it degrades.

## How to build
- Drive /tdd. Red first, from a real fixture in fixtures/, never a synthesised workbook.
- One vertical slice per commit. A slice is: a failing test, the code, the test passing.
- Touch one module per commit. If a change needs `audit/` and `patch/` together, that is
  two commits and probably two slices.
- Run the full suite after each slice, not at the end.

## Before you say you're done
- Every §7 test for the touched rules passes.
- The idempotency test passes: repair twice, second run finds nothing.
- If you touched `patch/`, the presentation diff (§6.5) is clean on every fixture.
- Any new trap you hit is written into docs/mind/brain/Gotchas.md, in the same branch.
- New vocabulary is in CONTEXT.md.
- Run /code-review using prompts/001-review.md before opening the PR.

## Commits
`<area>: <imperative, lowercase, ≤72 chars>`. No co-author trailer. No tool attribution.
No body unless the diff doesn't explain the why.
````

---

#### `prompts/001-review.md`

````markdown
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
````

---

#### `prompts/002-architect.md`

````markdown
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
````

---

## §2. Architecture

```
┌──────────────────┐  hx-post /scan    ┌──────────────────────────────┐
│  Browser         │ ────────────────▶ │  FastAPI + Jinja2            │
│  one HTML page   │ ◀──────────────── │   ├─ audit/     rule engine  │
│  + htmx          │  HTML fragment    │   ├─ patch/     XML editor   │
│  (no build step) │                   │   ├─ verify/    diffing      │
└──────────────────┘  hx-post /fix     │   ├─ store/     temp files   │
       │            ────────────────▶  │   └─ templates/ fragments    │
       │            ◀──────────────    └──────────────────────────────┘
       │              diff table                    │
       └─ <a href="/download/{job}">        soffice --headless
          plain link, not htmx              (recalculate formulas)
```

**Why htmx.** The real state of this workflow lives on the server: the temp file, the scan
result, the approved fix list, the diff. An SPA would have to mirror that state on the
client and keep the two in sync. With htmx the server renders HTML and state exists in
exactly one place. The trade: no build step, no bundle, no client state management.

**Why a Python backend is mandatory.** Reading Excel in the browser is fine; writing it
back is not — every free JS library loses styling on save. Principle §1.1 rules out a
frontend-only design.

**Stack:**

| Component | Choice | Reason |
|---|---|---|
| API | FastAPI + uvicorn | async, clean multipart upload, easy background tasks |
| Read/write xlsx | `zipfile` + `lxml` (tier A) | edits the XML directly, loses nothing |
| Read/write xlsx | `openpyxl` (tier B) | fallback only, when tier A can't handle it |
| Recalculation | LibreOffice headless | verifies formulas after patching |
| Frontend | htmx 2.x + Jinja2 | server-rendered fragments, no build, no client state |
| CSS | one hand-written `app.css` | enough for a single page, avoids a dependency |
| Tests | pytest + real xlsx fixtures | see §7 |

---

## §3. Directory layout

```
excel-doctor/
├── AGENTS.md                     # shared foundation — all three agents read it (§1b)
├── CLAUDE.md                     # one line: "Read AGENTS.md."
├── GEMINI.md                     # Antigravity-only overrides (empty to start)
├── skills/                       # canonical: mattpocock/*, ponytail, xlsx-internals
├── prompts/                      # 000-implement, 001-review, 002-architect, then NNN-*
├── .claude/                      # Claude Code adapter (skills symlink + settings.json)
├── .codex/                       # Codex adapter (config.toml → ../skills, ../prompts)
├── .agents/                      # Antigravity adapter (rules/, skills↗, workflows/)
├── CONTEXT.md                    # shared language — read before every session
├── docs/mind/                    # obsidian-mind vault (brain/, work/, reference/)
├── scripts/install-hooks.sh      # copies commit-msg + pre-commit guards into .git/hooks
├── .github/workflows/ci.yml      # runs the §7 suite + workflow-rule checks on every PR
├── backend/
│   ├── app.py                    # FastAPI routes
│   ├── model.py                  # Finding, FixPlan, DiffEntry (pydantic)
│   ├── workbook/
│   │   ├── reader.py             # xlsx → intermediate model
│   │   ├── formula.py            # tokenizer + reference normalization
│   │   └── inventory.py          # what's inside the file (charts, pivots, vba…)
│   ├── audit/
│   │   ├── base.py               # Rule class, registry
│   │   ├── rules_formula.py      # R01–R08
│   │   ├── rules_datatype.py     # R09–R14
│   │   ├── rules_format.py       # R15–R20
│   │   └── rules_structure.py    # R21–R23
│   ├── patch/
│   │   ├── xml_patcher.py        # tier A — edits inside the zip package
│   │   ├── openpyxl_patcher.py   # tier B
│   │   ├── styles.py             # add numFmt without breaking existing xf
│   │   └── rename_sheet.py       # rename a sheet + update every reference
│   ├── verify/
│   │   ├── recalc.py             # invoke soffice, re-read values
│   │   └── differ.py             # cell-by-cell before/after comparison
│   ├── templates/
│   │   ├── index.html            # the only full page, loads htmx from CDN
│   │   └── partials/
│   │       ├── _scanning.html    # scan-in-progress state, self-polling
│   │       ├── _report.html      # inspection slip + issue groups
│   │       ├── _findings.html    # one page of results for one rule
│   │       ├── _diff.html        # before/after diff table
│   │       ├── _ready.html       # download button + summary
│   │       └── _error.html       # error message
│   ├── static/app.css
│   └── tests/                     # layers 1–5, plus golden/ — see §7
│       ├── conftest.py
│       ├── fixtures_meta.yaml
│       ├── rules/  patch/  verify/  web/
│       └── golden/               # committed before/after pairs + diff.json
└── fixtures/                     # real xlsx files for testing (read-only control)
```

---

## §4. Audit rules

Every rule is a class extending `Rule`:

```python
class Rule:
    id: str                  # "R04"
    title: str               # short, Vietnamese (user-facing)
    why: str                 # 1–2 sentences on the damage, Vietnamese, for an accountant
    severity: Literal["error", "warning", "style"]
    risk: Literal["safe", "display", "value"]   # does fixing it change a number?
    auto_fixable: bool

    def detect(self, wb: WorkbookModel) -> list[Finding]: ...
    def fix(self, wb: WorkbookModel, finding: Finding) -> list[CellEdit]: ...
```

`risk` drives the whole frontend experience:
- `safe` — fixing changes no value at all (stripping whitespace, unifying number formats).
- `display` — changes how a value is shown, not what is stored (serial number → date).
- `value` — **changes a number**. Approved per cell, unchecked by default.

### Rule table

| ID | Rule | Sev | Risk | Detection | Fix |
|---|---|---|---|---|---|
| R01 | Formula contains `#REF!` | error | value | `#REF!` substring inside `<f>` | infer the intended reference from neighbours in the same column, propose it, **never auto-apply** |
| R02 | Cell currently evaluates to an error | error | value | `t="e"`, or `<v>` holds an error token | trace back to the root error cell in the dependency chain; report only |
| R03 | Error code pasted in as literal text | error | value | no `<f>`, string value matches `#(REF!\|VALUE!\|N/A\|NAME?\|DIV/0!\|NUM!\|NULL!\|ERROR!)` | clear to empty or 0 depending on the column's type |
| R04 | Arithmetic directly on a cell that returns `""` | error | display | formula is refs and `+-*/` only, and one ref points at a cell whose formula contains `""` | wrap each ref in `N()`; for `*` and `/` use `IFERROR(...,0)` |
| R05 | Reference to a sheet that doesn't exist | error | value | `Sheet!` token not in the sheet list | report only |
| R06 | Running-balance chain skips a row | warning | value | formula `=X{n}±…` where `X` is the cell's own column and `n ≠ row-1`; only in columns with ≥4 correctly linked cells | rewrite `n` to `row-1` |
| R07 | Empty cell breaks a formula chain | warning | value | cell empty, cells above and below in the same column both have `<f>` | fill by translating the formula below up one row |
| R08 | Formula is an outlier in its column | warning | value | normalize formulas to relative patterns; cells above and below match each other but not this one | propose the neighbours' pattern |
| R09 | Number stored as text | warning | value | `t="s"`/`inlineStr` whose content parses as a number | coerce to numeric, auto-detecting thousands and decimal separators |
| R10 | Date stored as text | warning | value | string matching `d/m/y`, `d-m-y`, `d.m.y` | convert to serial + a date numFmt |
| R11 | Date rendered as a serial number | warning | display | column header contains "ngày"/"date", numeric cell in 30000–80000, numFmt is not a date | apply `dd/mm/yyyy` |
| R12 | Boolean or percentage stored as text | warning | value | `"TRUE"`, `"12%"` | coerce to the matching type |
| R13 | Percentage stored at the wrong scale | warning | value | numFmt is `%` but the value is an integer > 1 | report only — too ambiguous to auto-fix |
| R14 | Stray whitespace and invisible characters | style | safe | `v != v.strip()`, `\u00a0 \u200b \u200c \ufeff \u200e \u200f`, doubled spaces, non-NFC strings | trim, NBSP → space, drop invisibles, normalize to NFC |
| R15 | Sheet name contains special characters | error | safe | `[ ] : \ / ? *`, comma, period, apostrophe, leading/trailing space, length > 31 | rename + update every reference (§5.3) |
| R16 | Inconsistent number format within a column | style | display | group numFmt per column, skipping the first 8 header rows; flag a minority group of ≤3 cells that is under 1/10 of the majority | apply the majority's numFmt |
| R17 | Locale-ambiguous date format | style | display | numFmt starts with `mm-dd` or `m/d/yy` | switch to `dd/mm/yyyy` |
| R18 | Fragile format code | style | display | numFmt contains `_)`, `\(`, `[$-409]`, `[Red]` with odd escaping | reduce to the equivalent standard code |
| R19 | Inconsistent fonts | style | display | group (font name, size) workbook-wide, flag groups under 1% | apply the majority font |
| R20 | Functions only available in newer Excel | warning | safe | `XLOOKUP XMATCH FILTER UNIQUE SORTBY SEQUENCE LET LAMBDA TEXTJOIN IFS SWITCH MAXIFS MINIFS CONCAT` | warn only, suggest `INDEX/MATCH` |
| R21 | Bloated used range | style | safe | declared dimension far exceeds the last cell with content | shrink `<dimension>`, cut file size |
| R22 | Broken defined name | warning | safe | definition contains `#REF!` | delete the dead name |
| R23 | Stray empty sheet | style | safe | no cell has content and no sheet references it | propose deletion, unchecked by default |

**Requirement on `why`.** Written for a warehouse accountant, not a developer.
Good: *"SUM và SUMIF bỏ qua các ô này. Nhìn thì giống số nhưng không cộng được."*
Bad: *"Cell type is inlineStr instead of numeric."*

---

## §5. Patch engine

### 5.1 Choosing a tier

Before patching, `inventory.py` opens the zip and reads `[Content_Types].xml` and
`xl/_rels/`. If any of the following is present, **tier A is mandatory**, because
openpyxl would drop it:

- `xl/charts/`, `xl/drawings/`, `xl/media/` — charts and images
- `xl/pivotCache/`, `xl/pivotTables/` — pivot tables and slicers
- `xl/vbaProject.bin` — macros
- `xl/threadedComments/`, `xl/persons/` — threaded comments
- `xl/tables/` — ListObjects
- external links under `xl/externalLinks/`
- conditional formatting using the `x14` extension
- sparklines, form controls, ActiveX

Surface it in the report: *"File có biểu đồ và macro, đang dùng chế độ sửa an toàn."*

### 5.2 Tier A — patch the XML directly

Flow: unzip to a temp dir → parse `xl/worksheets/sheetN.xml` with `lxml` → apply
`CellEdit`s → rewrite only the XML parts that changed → rezip, **preserving the original
entry order and compression level**.

A `CellEdit` is exactly one of four operations:

```python
SetValue(sheet, ref, value, cell_type)   # change <v> and the t attribute
SetFormula(sheet, ref, formula)          # change <f>, drop the cached <v>
SetNumFmt(sheet, ref, code)              # change the s attribute → a new xf
ClearCell(sheet, ref)                    # drop <v> and <f>, keep s untouched
```

Mandatory write rules:

- Changing any `<f>` → **delete `xl/calcChain.xml`** and remove it from
  `[Content_Types].xml` and `workbook.xml.rels`. Leave it and Excel calls the file corrupt.
- Changing `<f>` → also drop that cell's `<v>` so Excel recomputes on open.
- Set `<calcPr fullCalcOnLoad="1"/>` in `workbook.xml`.
- Preserve every other attribute of the `<c>` element, especially `s` (the style index)
  and `cm`, `vm`, `ph`.
- A `t="s"` cell points into `sharedStrings.xml` by index. When converting it to a number,
  **do not remove the shared-strings entry** — other cells may share it. Only change the
  cell's `t` and `<v>`.
- `t="inlineStr"` cells carry `<is><t>` inside the sheet itself; handle them separately.

### 5.3 Renaming a sheet

The most far-reaching operation here. Miss one location and the file breaks. Update
**all** of these:

1. `xl/workbook.xml` → `<sheet name="…">`
2. `<definedName>` entries in `workbook.xml`
3. Every `<f>` in every `xl/worksheets/sheetN.xml`
4. `<f>` in `xl/charts/chart*.xml` (chart series references)
5. Formulas inside conditional formatting and data validation
6. `xl/pivotCache/pivotCacheDefinition*.xml` → `<worksheetSource sheet="…">`
7. `printerSettings` and `<autoFilter>` where they reference the sheet absolutely

When substituting inside formulas, distinguish `'Sheet name'!` (quoted) from `Sheetname!`
(unquoted), and **never substitute inside a string literal** — in
`SUMIF(A:A,"nl_MUỐI,",B:B)` the sheet-looking text is data, not a reference. Use the
tokenizer in `workbook/formula.py`. Never a raw `str.replace`.

### 5.4 Adding a number format without wrecking styles

This is the easiest way to ruin a file's appearance. A cell's `s` points at `cellXfs[i]`,
and an `xf` bundles font, fill, border, alignment *and* numFmt together. Changing numFmt
by editing `cellXfs[i]` also restyles **every other cell sharing index `i`**.

The correct approach:

```
def ensure_xf(styles, base_xf_index, num_fmt_code) -> int:
    1. find the numFmtId for the code; if absent, create a numFmt with id >= 164
    2. clone cellXfs[base_xf_index] into a new xf, changing only numFmtId
       and setting applyNumberFormat="1"
    3. if an identical xf already exists, return its index (keeps styles.xml from bloating)
    4. append to cellXfs and return the new index
```

Required test: change one cell's numFmt, reopen the file, confirm a neighbouring cell that
shared the original style still has its font, fill and borders.

---

## §6. Verification and the diff table

After patching, run this chain — **if it fails, no download**:

1. **It reopens.** Re-read the zip, parse every XML part. A parse error → abort, return
   the original.
2. **Nothing went missing.** Compare the zip entry lists before and after. The only
   permitted absence is `calcChain.xml`. Anything else missing → abort.
3. **It recalculates.** Run `soffice --headless --convert-to xlsx` on a copy and count
   error cells. The count after must be **≤** the count before.
4. **Cell-by-cell diff.** Read cached values before and after, emit `diff.json`:

```json
{"sheet":"Nhập xuất tồn","ref":"Q16","before":0,"after":10000,
 "cause":"R07","note":"Dòng 16 bị trống làm đứt chuỗi tồn Đường"}
```

`_diff.html` shows this table **before** offering the download, grouped by cause, stating
plainly how many cells changed value. This is the single most important screen in the
product.

5. **Presentation diff.** For each sheet, extract the tuple `(font, fill, border, numFmt,
   column width, row height, merges)` before and after. It may differ only on cells named
   in a `CellEdit`. Any difference outside that list → abort and raise an internal error.

---

## §6b. Frontend with htmx

One `index.html`, loading htmx from a CDN. Every screen is an HTML fragment rendered by
the server and swapped into `#app`. No JavaScript beyond the three exceptions at the end
of this section.

### Screen flow

```
[1] Drop a file        →  hx-post /scan          →  swap #app = _scanning.html
[2] Scanning           →  hx-get /scan/{job}     →  self-polls, then swaps = _report.html
[3] Inspection slip    →  tick the groups to fix
                       →  hx-post /fix           →  swap #app = _diff.html
[4] Diff table         →  approve, or go back
                       →  hx-post /fix/confirm   →  swap #app = _ready.html
[5] Ready              →  <a href="/download/{job}"> download
```

### Endpoint contract

Every endpoint below returns an **HTML fragment**, not JSON.

| Method | Path | Returns | Notes |
|---|---|---|---|
| `POST` | `/scan` | `_scanning.html` | accepts multipart, creates a `job_id`, runs the scan as a background task |
| `GET` | `/scan/{job}` | `_scanning.html` or `_report.html` | polled by the client; on completion send `HX-Trigger: scanDone` |
| `GET` | `/findings/{job}` | `_findings.html` | params `rule`, `q`, `page`; powers filtering and pagination |
| `POST` | `/fix/{job}` | `_diff.html` | body is the checkbox form `fix=R14&fix=R15…` |
| `POST` | `/fix/{job}/confirm` | `_ready.html` | commits, produces the output file |
| `GET` | `/download/{job}` | binary `.xlsx` | **not through htmx**, see trap 15 |
| `GET` | `/report/{job}.csv` | CSV | plain link |

`job_id` is a UUID bound to a temp directory, with a one-hour TTL and automatic cleanup.
No login needed, but `job_id` must be unguessable so nobody can reach someone else's file.

### The htmx attributes you need

**Upload** — `hx-encoding` is mandatory; without it the file never reaches the server:

```html
<form hx-post="/scan" hx-encoding="multipart/form-data"
      hx-target="#app" hx-swap="innerHTML"
      hx-indicator="#spinner">
  <input type="file" name="file" accept=".xlsx,.xlsm" required>
  <button type="submit">Kiểm tra file</button>
</form>
```

**Poll while scanning** — a large file takes 20 seconds; never block the request:

```html
<div hx-get="/scan/{{ job }}" hx-trigger="every 1s"
     hx-target="#app" hx-swap="innerHTML">
  Đang quét {{ done }}/{{ total }} sheet…
</div>
```

When the scan finishes the handler returns `_report.html`, which carries no `hx-trigger`,
so the polling loop stops by itself. Don't use a recursive `hx-trigger="load delay:1s"` —
it strands orphaned loops.

**Filter and search** — the server answers as the user types:

```html
<input type="search" name="q" placeholder="Lọc theo sheet hoặc ô…"
       hx-get="/findings/{{ job }}" hx-trigger="keyup changed delay:300ms, search"
       hx-target="#findings" hx-swap="innerHTML">
```

**Paginate long lists** — rendering 900 findings at once freezes the page. Return 50 rows
per group; the last row loads the next page when scrolled into view:

```html
<tr hx-get="/findings/{{ job }}?rule={{ rule }}&page={{ page+1 }}"
    hx-trigger="revealed" hx-swap="afterend" hx-target="this">
  <td colspan="3">Đang tải thêm…</td>
</tr>
```

**Expand a group** — load detail on click, not upfront:

```html
<details hx-get="/findings/{{ job }}?rule={{ r.id }}"
         hx-trigger="toggle once" hx-target="find .hits">
```

**Select groups to fix** — a plain form, letting the browser collect the checkboxes:

```html
<form hx-post="/fix/{{ job }}" hx-target="#app">
  <input type="checkbox" name="fix" value="R14" checked>   <!-- safe -->
  <input type="checkbox" name="fix" value="R06">           <!-- value: not pre-checked -->
  <button>Xem trước thay đổi</button>
</form>
```

### The three places JavaScript is allowed

Outside these three, write none:

1. **Drag and drop.** htmx doesn't handle `drop`. About 15 lines to assign
   `dataTransfer.files[0]` to the input and call `form.requestSubmit()`.
2. **Showing the selected filename** before submit.
3. **Warning before leaving the page** while a job is running.

### Requirements on the HTML itself

- The page must work at a basic level with JavaScript disabled: the upload form is a real
  form with `action="/scan"`, and when the server sees a request without the `HX-Request`
  header it returns the full page instead of a fragment. This also happens to be the
  easiest way to test the backend.
- Each fragment is self-contained and renderable in a test without a browser.
- Keep each rule's `why` in the template. Don't ship it as JSON and render it with JS.

---

## §7. Tests

### The loop, not just the suite

Testing here is red-green-refactor driven from `prompts/000-implement.md`, not a batch run
at the end. Every slice starts with a failing test against a **real fixture**, and no slice
is done until the whole suite is green. The `/tdd` skill owns the rhythm; this section owns
what the tests must cover and where they live.

```
backend/tests/
├── conftest.py            # fixture loaders, the recalc helper, the presentation-diff helper
├── fixtures_meta.yaml     # per fixture: expected inventory, known defects, per-rule counts
├── rules/                 # one file per rule — Rxx_test.py
├── patch/                 # tier-A write correctness, style isolation, sheet rename
├── verify/                # the §6 chain, including every abort path
├── web/                   # endpoint + fragment tests, no browser
└── golden/                # committed before/after pairs + their diff.json
```

### Five layers, cheapest first

Run them in this order; a failure in an early layer means don't bother with the later ones.

1. **Tokenizer and reader (unit).** `formula.py` splits refs, quoted strings and functions;
   `reader.py` classifies cell types. Pure functions, milliseconds, no files. These catch
   the trap-3 (`=` stripping) and trap-8 (quoted sheet name) class before they reach a rule.
2. **Rule detect/fix (unit, fixture-backed).** For each rule: load the fixture, assert the
   **exact** finding count and locations, apply the fix, re-detect, assert zero. Counts come
   from `fixtures_meta.yaml`, never hard-coded in the test body — when a fixture changes, one
   file updates.
3. **Patch integrity (integration).** After any `CellEdit`: the file reopens, the zip entry
   list lost only `calcChain.xml`, the touched cell changed, and — the load-bearing one —
   the **presentation diff is empty except on edited cells** (§6.5). This is the layer that
   proves "we didn't wreck the formatting", so it runs on every fixture that has styling.
4. **Verification chain (integration).** Drive §6 end to end, and assert each abort path
   actually aborts and returns the original: feed it a patch that drops a chart, a patch that
   raises the error count, a patch that corrupts XML. A verification step with no failing test
   is a verification step you don't trust.
5. **Web (integration, no browser).** Hit the endpoints with `httpx.AsyncClient`. Assert each
   returns a fragment (not JSON), that a request without the `HX-Request` header returns the
   full page (the no-JS path from §6b), that `/download` returns `.xlsx` bytes not HTML, and
   that fix selection is remembered server-side across a filter (trap-13). Fragments render in
   isolation because each is self-contained.

Browser-level behaviour (drag-drop, the polling loop actually stopping) is checked by hand
against the acceptance list, not automated — the three JS snippets from §6b are too thin to
earn a Playwright dependency, and ponytail says don't add it.

### Fixtures are the control — treat them as read-only

`fixtures/` holds **real files, never files this codebase generated**, because a workbook we
wrote round-trips through our own assumptions and hides the very bugs we're hunting. The deny
rule in `AGENTS.md` forbids editing them; a test that needs a mutated file copies it to a
tmp path first.

| Fixture | What it exercises |
|---|---|
| `sokho_google.xlsx` | exported from Google Sheets — `""` treated as 0, `#ERROR!` tokens |
| `chart_pivot.xlsx` | charts + pivot + slicer → must select tier A |
| `macro.xlsm` | `vbaProject.bin` survives |
| `shared_formula.xlsx` | shared formulas, `t="shared" si="0"` |
| `inline_str.xlsx` | inline strings instead of sharedStrings |
| `date1904.xlsx` | workbook on the 1904 date system |
| `cf_datavalidation.xlsx` | conditional formatting + data validation |
| `huge.xlsx` | 200k cells, scan must finish under 20 seconds |
| `corrupt.xlsx` | a broken file — must fail gracefully, never crash |

Every fixture is described in `fixtures_meta.yaml`: what the inventory should report, which
defects it carries, and the exact per-rule finding count. Adding a rule usually means adding
a fixture and a row here; a new trap found mid-build (trap into `Gotchas.md`) usually means a
new fixture that reproduces it, committed in the same branch as the fix.

### Golden files

For the end-to-end path, commit `golden/<fixture>.after.xlsx` and `golden/<fixture>.diff.json`
next to each input. The test repairs the input with a fixed fix-set and asserts the result
matches the golden pair. When a fix legitimately changes output, the diff is reviewed like
any code change and the golden file is updated in the same commit — a golden update is never
a silent side effect. This is what stops a well-meaning refactor from quietly moving a number.

### The three tests that outrank the rest

- **Idempotency.** Repair twice in a row; the second run finds nothing to fix and produces a
  byte-comparable file. This is the single strongest signal that fixes are complete and
  side-effect-free, and it runs on every fixture.
- **Presentation invariance.** Across the whole suite, the only style/format/geometry deltas
  are on cells named in a `CellEdit`. One failure here blocks a merge outright.
- **Original-on-failure.** When verification aborts, the bytes handed back equal the input
  byte-for-byte. A repair tool that returns a half-patched file on failure is worse than one
  that does nothing.

### CI gate — mirrors the merge rule

`main` stays green (git flow, §1b), so the same suite runs in CI on every PR and a branch
can't squash-merge until it passes. One workflow, agent-agnostic — it doesn't care whether
Claude Code, Codex or Antigravity wrote the diff.

```yaml
# .github/workflows/ci.yml (sketch)
# 1. install python + libreoffice (recalc needs soffice)
# 2. install deps, install git hooks via scripts/install-hooks.sh
# 3. ruff + mypy
# 4. pytest -q  (layers 1–5)
# 5. assert every prompts/NNN-*.md on the branch maps to a commit, and
#    no commit message carries a banned trailer  (git log check)
```

Step 5 makes the workflow rules from §1b machine-checked rather than trusted: a PR whose
history skipped the prompt file, or slipped in a co-author trailer, fails CI the same way a
broken test does. Local pre-commit/commit-msg hooks catch it first; CI is the backstop for
whoever didn't install them.

Coverage is a floor, not a goal: `patch/` and `verify/` at 100% branch coverage because
their abort paths are the safety net; rules pragmatic; UI glue uncovered by design.

---

## §8. Build order

| # | Milestone | Done when |
|---|---|---|
| 0 | Repo setup per §1b | root `AGENTS.md` + `CLAUDE.md`/`GEMINI.md` pointers written; `skills/` and `prompts/` populated; `.claude/`, `.codex/`, `.agents/` adapters point back at them; vault at `docs/mind/`; `scripts/install-hooks.sh` installs the commit-msg and pre-commit guards; first `CONTEXT.md` drafted from a `/grill-with-docs` session |
| 1 | `reader.py` + `inventory.py` | reads every fixture, correctly lists charts/pivots/vba |
| 2 | `formula.py` tokenizer | splits refs, strings and functions correctly; tested against formulas with Vietnamese sheet names and commas |
| 3 | Rules R01–R05 + `/scan` | correct report on `sokho_google.xlsx` |
| 4 | htmx page + `_report.html` | upload shows the inspection slip; filtering, pagination and CSV export work |
| 5 | `xml_patcher.py` + R14, R15 (the `safe` group) | patch applies; §6 steps 1, 2 and 5 all pass |
| 6 | `styles.py` + R11, R16–R19 (the `display` group) | neighbouring cells sharing a style are untouched |
| 7 | `verify/` + `_diff.html` + `_ready.html` | diff table is correct; download blocked when verification fails |
| 8 | The `value` group, R06–R10 | unchecked by default, approved per cell |
| 9 | Remaining rules + performance | 200k-cell file scans in under 20 seconds |

After each milestone: run the full test suite, report results, wait for approval before
continuing. Close each one with `/om-wrap-up`, and `/om-weekly` when a milestone lands.

Every milestone starts with a prompt file and ends with a squash-merged PR pointing at it.

---

## §9. Known traps

Everything below was verified against real files. None of it is speculation.

1. **Google Sheets and Excel disagree about `""`.** For `=A1+B1` where `B1` returns an
   empty string, Google produces a number and Excel produces `#VALUE!`. A Google-exported
   file carries the "correct" cached value, so the file looks fine until someone opens it
   in Excel. This is the most common and least visible defect there is. R04 exists for it.

2. **Google writes its error token as `#ERROR!`** with `t="str"`, not `t="e"`. The error
   detector must catch both shapes, and must distinguish a cell that **has** a formula
   (a computed error) from one that **doesn't** (a pasted-in literal).

3. **JS libraries strip the leading `=` from formulas.** Every regex anchored on `^=` will
   silently match nothing. Normalize to one shape at read time.

4. **LibreOffice doesn't implement all of Excel's functions.** `XLOOKUP`, `FILTER`,
   `UNIQUE` and `SEQUENCE` won't evaluate; post-2007 functions like `TEXTJOIN`, `IFS` and
   `CONCAT` need an `_xlfn.` prefix when written straight into the XML. Verification must
   tell "a real error" apart from "LibreOffice doesn't know this function", or it will
   raise false alarms.

5. **Not deleting `calcChain.xml` makes Excel declare the file corrupt.** This is the
   fastest way to destroy trust — the user opens the file and gets
   "Excel found unreadable content".

6. **Shared formulas (`t="shared"`).** Only the first cell holds the real formula; the
   rest carry just an `si`. Editing the first cell edits the whole group. Expand them into
   individual formulas before editing any one of them.

7. **The 1904 date system.** Read `<workbookPr date1904="1"/>`. Ignore it and every date
   is off by four years.

8. **Sheet renaming must skip quoted strings.** A sheet name can also appear as data in a
   `SUMIF` criterion. Substituting there breaks the logic.

9. **`s` is a shared style index.** Editing `cellXfs[i]` restyles every cell pointing at
   `i`. Always create a new `xf` instead of mutating an existing one. See §5.4.

10. **Auditing number formats across header rows produces garbage.** Many sheets carry a
    row numbering the columns `1, 2, 3…` right under the header. Exclude the first 8 rows
    from numFmt statistics.

11. **Is an empty cell mid-chain a bug or deliberate?** A machine can't tell. Always
    classify it as `value`, show the consequence in the diff table, and let the user decide.

12. **Some formula inconsistencies are intentional.** Two different formulas in one column
    may mean someone changed the logic from a certain row onward. Report it; don't
    auto-unify.

13. **An htmx swap replaces HTML, so client state disappears.** A user ticks six groups,
    then filters the list, and loses everything if the fragment gets swapped over. Either
    keep the tick state on the server keyed by `job_id`, or scope `hx-target` to a child
    region that never touches the form. Choose the first — truer to htmx and easier to test.

14. **Without `hx-encoding="multipart/form-data"` the file never arrives.** htmx defaults
    to urlencoded. This is the single most common mistake when pairing htmx with uploads.

15. **Never download a binary through htmx.** htmx takes the response and swaps it into
    the DOM, so the .xlsx contents spill out as text. Use a plain
    `<a href="/download/{job}">`, and if the page uses `hx-boost`, set `hx-boost="false"`
    on that link.

16. **Long jobs must poll; don't block the request.** Scanning a 200k-cell file takes 20
    seconds and a synchronous `hx-post` will hit a proxy timeout. Return the `job_id`
    immediately and let the client poll. The SSE extension is tidier, but one-second
    polling is sufficient and has fewer failure modes.

17. **Rendering 900 findings in one fragment freezes the page.** Paginate server-side from
    the start, rather than discovering it when you first test with a real file.

---

## §10. Definition of done

- Upload a file with 900 findings, repair it, rescan: under 10 remain.
- The downloaded file opens in Excel, WPS and LibreOffice with no error dialog.
- Charts, pivots, macros and images are intact.
- Every cell whose value changed appears in the diff table with its cause.
- A second repair pass finds nothing to fix.
- Someone who has never read this document still understands what each issue means and
  whether they should fix it.
- Every commit on `main` traces to a prompt file in `prompts/`.
- `git log` contains no co-author trailers and no tool attribution.
- `docs/mind/brain/Gotchas.md` has an entry for every trap hit during the build, not just
  the ones listed in §9.
