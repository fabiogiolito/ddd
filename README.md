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
├── data/             # what the app remembers
├── features/         # what the app does
├── pages/            # what people see
├── components/       # reusable UI pieces
├── integrations/     # auth, email, payments, APIs
└── .tech/            # technical decisions, for whoever reads code
```

1. **Docs first.** Every change, from a doc edit or a chat prompt, lands in `docs/` before it lands in code.
2. **Plan, then apply.** The agent shows what changed in the docs and what it will change in the code, then waits for a yes.
3. **Behavior, not implementation.** Docs say what the app does. Technical choices live in `docs/.tech/`.

Each feature doc ends with Given / When / Then acceptance criteria, which become tests.

### Noticing doc edits

`ddd/scripts/docs_status.py` compares `docs/` against the last applied build, with no file watcher or server:

```bash
python ddd/scripts/docs_status.py status        # what changed, what it affects, broken links
python ddd/scripts/docs_status.py diff features/approve-request
python ddd/scripts/docs_status.py mark-applied  # after code and tests match the docs
python ddd/scripts/docs_status.py restore features/approve-request
```

It stores a hash and a copy of each doc as last built in `docs/.state.json` and `docs/.state/`. Standard-library Python only.

## Install

- **Claude (web, desktop):** download [`ddd.skill`](ddd.skill), then add it under **Customize > Skills**.
- **Claude Code:** copy the `ddd/` folder into `~/.claude/skills/` (or `.claude/skills/` in a project).
- **Other agents:** point the agent at `ddd/SKILL.md`; it is plain markdown.

## Use

- `/ddd` reports what changed in the docs since the last build.
- `/ddd <request>` starts an app, applies a doc edit, or makes a change, following the docs-first workflow.

## Contents

| Path | What it is |
| --- | --- |
| `ddd/SKILL.md` | The workflow and rules the agent follows |
| `ddd/references/templates.md` | A template for each doc type |
| `ddd/scripts/docs_status.py` | Change tracking for `docs/` |
| `ddd.skill` | The packaged skill, ready to upload |
