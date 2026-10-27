# ddd — doc-driven development

A skill for AI agents that builds and changes apps from a folder of plain-language markdown docs. The docs are the source of truth; the code is generated from them and kept in line with them.

**Page:** https://fabiogiolito.github.io/ddd/

## Why

Most people building with AI no longer read the code. What matters is how the app works and what it does, and that is best said in natural language.

With `ddd` you keep asking the agent for what you want. For every request it updates the docs first, then the code. You don't have to write the docs: they are how you follow what the agent is doing, and they stay behind as reference for how the app works. You can edit them directly if you want, and the agent will update the code to match.

Because every change lands in the docs first, teammates can follow new features and changed rules by reading doc diffs in plain language instead of code diffs.

## How it works

```
docs/
├── app.md            # what the app is, who uses it, roles, glossary
├── roadmap.md        # phases and the order plans get built in
├── data/             # what the app remembers
├── features/         # what the app does
├── pages/            # what people see
├── components/       # reusable UI pieces
├── integrations/     # auth, email, payments, APIs
├── plan/             # committed work that isn't built yet
│   ├── ideas/        # loose ideas, not committed
│   └── done/         # plans that were built and merged, kept as a record
└── .tech/            # technical decisions, for whoever reads code
```

1. **Docs first.** Every change, from a doc edit or a chat prompt, lands in `docs/` before it lands in code.
2. **Plan, then apply.** The agent shows what changed in the docs and what it will change in the code, then waits for a yes.
3. **Behavior, not implementation.** Docs say what the app does. Technical choices live in `docs/.tech/`.

Each feature doc ends with Given / When / Then acceptance criteria, which become tests.

### Planning and the roadmap

Where a doc lives says what stage it's in, so the folder tree shows what's built and what's coming without opening a file:

| Stage | Where |
| --- | --- |
| Idea | `docs/plan/ideas/` |
| Planned, or in progress | `docs/plan/`, with `status: planned` or `status: in-progress` |
| Built | `docs/features/`, `docs/data/`, `docs/pages/`, … (no status) |
| Merged record | `docs/plan/done/` |

`docs/roadmap.md` lays the plans out in phases, as checklists in priority order:

```markdown
## Phase 1: Core
Goal: a host can create a dinner and guests can reply.
- [x] [[features/create-dinner]]
- [ ] [[plan/reminders]]
- [ ] Set up a sending domain for email
```

Plan a whole set of features without building anything, then have the agent take them one at a time: it marks each `in-progress`, builds it through the usual docs → plan → code loop, moves its doc to where it now belongs, checks it off, and stops for review. At the end of a phase it stops so you can try the app before the next one.

### Changing a feature that's already built

Built docs describe only what's live, so you can trust every rule in them. Planned work that touches a built feature is a plan of its own in `docs/plan/`:

- **An extension** adds a capability on top of a built feature: `extends: [features/rsvp]`, e.g. `plan/plus-ones.md`. It describes the new behavior and lists what will change in the feature it extends.
- **A change** adjusts existing behavior: `changes: [features/rsvp]`, e.g. `plan/close-replies-early.md`, saying what's true now and what will be true after.

When one is built, the agent writes it into the docs it targets. That edit is the doc diff reviewers read. The plan then moves to `plan/done/` as a record. If a target doc changes before its plan is built, `status` flags the plan to re-check.

### Noticing doc edits

`ddd/scripts/docs_status.py` compares `docs/` against the last applied build, with no file watcher or server:

```bash
python ddd/scripts/docs_status.py status        # what changed, what it affects, broken links
python ddd/scripts/docs_status.py diff features/rsvp
python ddd/scripts/docs_status.py mark-applied  # after code and tests match the docs
python ddd/scripts/docs_status.py restore features/rsvp
python ddd/scripts/docs_status.py roadmap       # progress per phase, anything out of sync
python ddd/scripts/docs_status.py next          # the next item to work on
```

It stores a hash and a copy of each doc as last built in `docs/.state.json` and `docs/.state/`. Standard-library Python only.

## Install

- **Claude (web, desktop):** download [`ddd.skill`](ddd.skill), then add it under **Customize > Skills**.
- **Claude Code:** copy the `ddd/` folder into `~/.claude/skills/` (or `.claude/skills/` in a project).
- **Other agents:** point the agent at `ddd/SKILL.md`; it is plain markdown.

## Use

- `/ddd` reports what changed in the docs since the last build.
- `/ddd plan <idea>` writes plans in `docs/plan/` and a phased roadmap, without building.
- `/ddd next` builds the next roadmap item and marks it done.
- `/ddd roadmap` shows progress per phase.
- `/ddd <request>` starts an app, applies a doc edit, or makes a change, following the docs-first workflow.

## Contents

| Path | What it is |
| --- | --- |
| `ddd/SKILL.md` | The workflow and rules the agent follows |
| `ddd/references/templates.md` | A template for each doc type |
| `ddd/scripts/docs_status.py` | Change tracking for `docs/` |
| `ddd.skill` | The packaged skill, ready to upload |
