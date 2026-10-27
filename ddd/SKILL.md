---
name: ddd
description: Build and change apps where a folder of linked markdown specs is the source of truth and code is generated from it. Use this whenever the user wants to start an app "spec-first" or "doc-driven", has a docs/ folder of feature, page, data or component docs, edits a spec doc and wants the app updated, asks what changed in the specs, wants to plan features, phases or a roadmap and work through them one at a time, or asks for any change to an app that already has a docs/ folder — even a small code tweak, because the docs must be updated first. Also use when a non-coder wants to understand or change how their app works by reading and editing docs instead of code.
---

# Doc-driven development

The app is described by a folder of plain-language markdown docs in `docs/`. Docs are upstream; code is downstream.

Most of the time the person just asks you for things in chat. You write the docs: for every request, update the docs first, then the code. The person isn't expected to write docs. The docs are how they follow what you're doing, a reference for how the app works, and a plain-language history that teammates can review instead of code diffs. They may also edit a doc directly; when they do, you bring the code in line with it.

Why this works: most people building with AI no longer read the code, but they do read prose. Making the prose structured, linked and authoritative turns the docs they were already generating into something they can own and change. The cost is an extra layer, so the layer has to stay honest: if docs and code disagree, the docs are wrong *or* the code is, and you must never let that go unnoticed.

## Invoking it as /ddd

- `/ddd` alone: run the status check (below) and report in two or three lines what changed in `docs/` since the last build and what it affects. If there's no `docs/` folder yet, offer to start a new app.
- `/ddd plan <idea or scope>`: plan features without building them. Write feature docs with `status: planned` and lay them out in phases in `docs/roadmap.md`.
- `/ddd next`: pick up the next roadmap item and take it through to done (see "Working through the roadmap").
- `/ddd roadmap`: show progress per phase and anything out of sync.
- `/ddd <request>`: treat the text as the request (start an app, apply a doc edit, make a change) and follow the matching workflow.

If the project already has a `docs/` folder used for something else (a README site, API docs), don't mix the two: ask before adding app docs there.

## The three rules

1. **Docs first, always.** Every change, whether it comes from a doc edit or a chat prompt, lands in `docs/` before it lands in code. A prompt like "make the button blue" becomes an edit to the relevant page or component doc, then a code change. Never edit code that changes behavior without the doc saying so.
2. **Plan, then apply.** Never rebuild code silently. Show what changed in the docs and what you intend to change in the code, and wait for a yes. Small, obvious changes can be planned and applied in one turn if the person has said they prefer that.
3. **Behavior, not implementation.** Readable docs describe what the app does and why. Technical choices live in `docs/.tech/`, which non-coders can ignore.

## Folder layout

```
docs/
├── app.md            # what the app is, who uses it, roles, glossary
├── roadmap.md        # phases and the order features get built in
├── data/             # what the app remembers: one doc per entity
├── features/         # what the app does: one doc per capability
├── pages/            # what people see: one doc per screen
├── components/       # reusable UI pieces used on several pages
├── integrations/     # what it talks to: auth, email, payments, APIs
└── .tech/            # technical decisions: stack, structure, conventions
```

Each folder answers one question, so a person always knows where to look. Add folders only when a new kind of question appears (for example `jobs/` for scheduled work).

Templates for every doc type are in `references/templates.md`. Read it before creating the first docs in a project or any doc of a type you haven't written yet in this session.

## Planning: feature status and the roadmap

The docs describe what the app does today *and* what it will do. Two things keep those apart:

- **Each feature doc has a `status`** in its frontmatter. It's the source of truth for where that feature stands:

  | Status | Meaning |
  | --- | --- |
  | `idea` | Worth remembering; not committed to. Can be a few lines. |
  | `planned` | Committed to. The doc is complete enough to build from: rules and acceptance criteria written. |
  | `in-progress` | Being built now. At most one at a time unless the person asks otherwise. |
  | `done` | Built, and its acceptance-criteria tests pass. |

  Data, page, component and integration docs don't carry a status. When they change for a feature that isn't built yet, mark the new parts in the text, e.g. a `*(planned: [[features/plus-ones]])*` note on the line, and remove the note when that feature is done.

- **`docs/roadmap.md` holds the order.** Each `##` heading is a phase, with a one-line goal. Under it, a checklist in priority order: feature links (`- [ ] [[features/reminders]]`) or plain tasks with no feature doc (`- [ ] Set up a sending domain for email`). A `## Ideas` section at the end holds unscheduled items. The checklist mirrors the statuses: checked means `done`. The template is in `references/templates.md`.

Why two places: a status belongs to the feature and travels with it; order and phases are a plan across features and change more often. Keeping each fact in one place means neither goes stale. Whenever you change a feature's status, update its checkbox in the same edit.

The script checks both: `roadmap` shows progress per phase and anything out of sync (a checked item that isn't done, a planned feature missing from the roadmap, an unknown status). `next` gives the item to work on: an `in-progress` one if there is one, otherwise the first unchecked item in the first scheduled phase.

```bash
python <skill-path>/scripts/docs_status.py roadmap --root <project-root>
python <skill-path>/scripts/docs_status.py next --root <project-root>
```

Changes to `idea` or `planned` docs (and to the roadmap) are reported by `status` as **plan only**: there's no code to update, so they don't need a build plan. Mention them, then run `mark-applied` once the person has seen them.

## Linking

- Frontmatter declares relationships: `uses:` (docs this one depends on) and `shown-on:` (pages where this appears). The status script builds the impact graph from these.
- In the body, link with wiki links: `[[data/rsvp]]`, `[[integrations/email#reminder]]`, `[[features/waitlist|the waitlist]]`. Paths are relative to `docs/`, without `.md`.
- Link the first mention of anything defined elsewhere. Don't redefine it.

## The altitude test

Every line in a readable doc should be something a product manager would say out loud in a meeting.

| Belongs in the doc | Belongs in `.tech/` or code |
| --- | --- |
| "Replies close when the dinner starts." | "Reject POST /rsvp when now() >= dinner.starts_at." |
| "The host gets an email for each new reply." | "Enqueue a job on the rsvp.created event." |
| "Times are shown in the dinner's own time zone." | "Store UTC; convert with the dinner's IANA zone on render." |

If a person writes implementation detail into a readable doc, keep their intent, move the detail to `.tech/`, and tell them where it went.

## Acceptance criteria are the contract

Every feature doc ends with Given / When / Then acceptance criteria. Generate a test for each one. Prose is ambiguous; tests pin down what the prose means, so two builds from the same doc behave the same. When a doc changes, update the matching tests in the same apply.

If a feature has no acceptance criteria, propose some in the plan rather than inventing behavior silently.

## Open questions block the build

Any `## Open questions` item that affects what you're about to build is a stop: point to it and ask, rather than guessing. Questions that don't touch the current change can stay open.

## Workflow

### Start of every turn in a doc-driven project

Run the status script first, so changes made outside the chat are never missed:

```bash
python <skill-path>/scripts/docs_status.py status --root <project-root>
```

It compares `docs/` against the last applied state (`docs/.state.json`) and reports added, changed and removed docs, which other docs link to them (the impact), and broken links. If nothing changed, carry on with the request. If something changed, say so before anything else and fold it into the plan — the person may have edited docs since the last turn and forgotten to mention it.

Use `diff` to see what exactly changed in one doc since it was last applied:

```bash
python <skill-path>/scripts/docs_status.py diff --root <project-root> docs/features/rsvp.md
```

This works because the script keeps a copy of every doc as it was at the last apply (in `docs/.state/`). Never edit those copies.

### Starting a new app

1. Ask what the app is for, who uses it and the 3–5 things it must do. Don't ask about technology unless the person brings it up.
2. Write `docs/app.md`, then the data docs, then one feature doc per capability (`status: planned`), then the pages. Use the templates.
3. Write `docs/roadmap.md`, following "Planning a set of features" below. For a small app a single phase is fine.
4. Write `docs/.tech/stack.md` with your technical choices, kept short.
5. Show the person the phases, a one-line summary of each feature and the open questions. They don't need to read every doc; point them to the feature docs if they want detail.
6. On their go-ahead, set up the project skeleton, then work through the roadmap one item at a time.

### A doc was edited (by the person or another tool)

1. Run `status`, then `diff` on each changed doc.
2. Read the impacted docs and check for contradictions. A change in one doc can break another (a field renamed in `data/` but still used in a feature). Contradictions are the most valuable thing you catch; list them and ask which side wins rather than picking one.
3. Present the plan (format below) and wait.
4. On approval: update any other docs the change requires, then the code, then the tests. Run the tests.
5. Run `mark-applied`.
6. If the person rejects the change, offer to restore the doc to its last applied version (`diff` shows it) or to leave it unapplied for later.

### A change was asked for in chat

1. Find the doc(s) the change belongs in, using the folder layout and the links. If it's a new feature and the project has a roadmap, ask whether to build it now or add it to the roadmap as `planned`. If built now, it still gets a feature doc, a roadmap line, and `status: done` at the end.
2. Edit the docs first and show the doc diff in plain language: what the doc said, what it says now.
3. Present the plan for the code, as above. For a small, unambiguous change, the doc diff and the plan can go in one message.
4. On approval, apply and `mark-applied`.

If the request is purely technical with no behavior change (a refactor, a dependency upgrade, a performance fix), it goes in `.tech/` or straight to code with a one-line note in `.tech/`, and needs no readable doc change.

### Planning a set of features

When the person describes several things they want, or asks for a plan (`/ddd plan`):

1. Break the request into features. One doc per capability a user would name ("reply to an invite", "get a reminder"), not per technical task.
2. Write each feature doc with `status: planned`: description, who, rules, acceptance criteria, open questions. Anything vague becomes an open question rather than a guess. Things mentioned in passing become `idea` docs or lines under `## Ideas`.
3. Group them into phases in `docs/roadmap.md`. A phase should leave the app usable on its own: phase 1 is the smallest version someone would actually use. Order items inside a phase by dependency first, then value. Put setup work (domains, accounts, data imports) in as plain tasks where it's needed.
4. Show the person the phases and the open questions, in a short list. Don't build anything. Ask them to answer the open questions for phase 1 and confirm the order.
5. Run `mark-applied` to record the plan as reviewed.

### Working through the roadmap

`/ddd next`, or "keep going", "what's next":

1. Run `next`. If an item is already `in-progress`, resume it; don't start another.
2. Read its feature doc and the docs it uses. If open questions affect it, ask now, before writing code.
3. Set `status: in-progress` and tell the person in one line what you're starting and what "done" means for it (its acceptance criteria, in brief).
4. Follow the normal plan-then-apply loop: any doc updates, then the plan, then on approval the code and tests. If the person has said to keep going without asking for each item, skip the approval only for items whose docs they've already reviewed.
5. When the tests pass: set `status: done`, check its box in `roadmap.md`, remove any `*(planned: …)*` notes for it in other docs, and run `mark-applied`.
6. Report in two or three lines: what's done, what's next, and how far along the phase is. Stop there unless asked to continue.
7. At the end of a phase, stop even if asked to keep going. Summarize the phase and ask the person to try the app before starting the next one, since phase boundaries are where plans change.

A plain task (no feature doc) is done the same way, without the doc steps: do it, check it off, note anything technical in `.tech/`.

If something new comes up while building (a missing rule, a feature the current one depends on), don't expand the current item silently. Add it to the roadmap as its own item, or as an open question, and mention it in the report.

### Mark the state applied

After code and tests match the docs:

```bash
python <skill-path>/scripts/docs_status.py mark-applied --root <project-root>
```

Only run this when the build actually succeeded and tests pass. Marking applied with broken code makes the next `status` lie.

### Drift check

If the person edited code directly, or you suspect the code no longer matches the docs, compare behavior against the acceptance criteria and the docs. Report mismatches as a list ("the code lets guests reply after the dinner has started; `rsvp.md` says replies close at the start"). Ask whether to update the doc to match the code or fix the code to match the doc. Never resolve drift silently in either direction.

## Plan format

Keep it short and readable by a non-coder. Lead with what changes for users, not files.

```
**What changed in the docs**
- features/rsvp.md: guests who are going can bring one plus-one.

**What this means for the app**
- Guests replying "going" can add a plus-one's name.
- Plus-ones take a seat, so "seats left" counts them.

**Also affected**
- data/rsvp.md: new plus-one field. components/guest-list.md: plus-ones listed under their guest.

**Conflicts or questions**
- None.

**Code changes**: 4 files, 2 tests added.

Apply?
```

Leave out sections that are empty, except "Conflicts or questions" when there's any doubt.

## Writing style for docs

- Short sentences, plain words, present tense: "A guest replies…", not "The system shall allow…".
- One idea per bullet. Rules as bullets, flows as state lists, fields as tables.
- Use the glossary terms from `app.md` consistently; if a new term appears, add it there.
- Don't put numbers or copy in two places. Define once, link elsewhere.
