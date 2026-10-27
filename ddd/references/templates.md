# Doc templates

One template per doc type. Copy the shape, not the example content. Sections marked *(optional)* can be dropped when empty; everything else stays, even if short. The examples describe a small dinner-club app: hosts create dinners and invite friends, guests reply.

Contents: app.md · roadmap.md · data · features · extensions · changes · pages · components · integrations · .tech

---

## docs/app.md

```markdown
---
type: app
---

# <App name>

<One or two sentences: what the app is for and for whom.>

## Who uses it
| Role | What they do |
|------|--------------|
| Host | Creates dinners, invites people, sees the guest list |
| Guest | Replies to an invite, sees who else is coming |

## What it does
- [[features/create-dinner]]
- [[features/rsvp]]

## Glossary
- **Dinner**: one event with a date, a place and a seat limit.
- **RSVP**: a guest's reply: going, maybe or can't go.

## Out of scope *(optional)*
- Payments, splitting the bill.
```

---

## docs/roadmap.md

```markdown
---
type: roadmap
---

# Roadmap

## Phase 1: Core
Goal: a host can create a dinner and guests can reply.
- [x] [[features/create-dinner]]
- [ ] [[features/rsvp]]
- [ ] [[features/reminders]]
- [ ] Set up a sending domain for email

## Phase 2: Bigger dinners
Goal: dinners with plus-ones and waitlists.
- [ ] [[features/plus-ones]]
- [ ] [[changes/close-replies-early]]
- [ ] [[features/waitlist]]

## Ideas
- [ ] [[features/photos]]
- Splitting the bill
```

- Each `##` is a phase with a one-line goal. Phase 1 is the smallest version someone would use.
- Items are in priority order. A checked box means the feature's status is `done`.
- Feature and change items link to their doc. Setup work with no doc is a plain line.
- `## Ideas` (or `## Backlog`) is never picked up by `next`. Items there may have a checkbox or not.

---

## docs/data/<entity>.md

```markdown
---
type: data
---

# <Entity name>

<One sentence: what this record represents.>

| Field | Meaning | Required |
|-------|---------|----------|
| guest | [[data/person]] who was invited | yes |
| dinner | [[data/dinner]] they replied to | yes |
| answer | going, maybe or can't go | yes |
| note | message to the host | no |

## Rules *(optional)*
- One RSVP per guest per dinner. A new reply replaces the old one.

## Who can see it *(optional)*
- The guest and the host.
```

Field names are written as people say them, not as column names. `.tech/` maps them to code if needed. Only fields that exist today belong here; a field a planned feature will add is listed in that feature's doc until it's built.

---

## docs/features/<feature>.md

```markdown
---
type: feature
status: planned
uses: [data/rsvp, data/dinner, integrations/email]
shown-on: [pages/dinner]
---

# <Verb phrase: "Reply to an invite">

<One or two sentences: what happens and why it matters.>

## Who
- Anyone with the invite link.
- Guests don't need an account. They give their name and email once.

## Rules
- Replies close when the dinner starts.
- If the dinner is full, new "going" replies join a waitlist.

## States *(optional, when something moves through stages)*
invited → going | maybe | can't go
going → can't go (frees a seat)

## What happens after *(optional)*
- Host gets [[integrations/email#new-reply]]

## Acceptance criteria
- Given a dinner with seats left, when a guest replies "going",
  then they appear on the guest list.
- Given a full dinner, when a guest replies "going",
  then they join the waitlist.

## Open questions *(optional)*
- Should guests see who said maybe?
```

`status` is one of `idea`, `planned`, `in-progress`, `done`. An `idea` doc can be just the title, a sentence and its open questions; it needs rules and acceptance criteria before it becomes `planned`.

---

## docs/features/<feature>.md that extends a built feature

```markdown
---
type: feature
status: planned
extends: [features/rsvp]
uses: [data/rsvp]
---

# Bring a plus-one

Guests who are going can bring one person with them.

## Rules
- Guests who are going can add one plus-one, by name.
- A plus-one takes a seat. If there's room for the guest
  but not the plus-one, both join the waitlist.
- Plus-ones show on the guest list under who brought them.

## Changes to rsvp
- "Each invite is for one person" no longer applies.
- An RSVP gets a plus-one field: their guest's name, if any.
- [[components/guest-list]] lists plus-ones under their guest.

## Acceptance criteria
- Given a guest going with a plus-one, then "seats left"
  drops by two.
- Given one seat left, when a guest replies going with a
  plus-one, then both join the waitlist.

## Open questions
- Can a host turn plus-ones off for a dinner?
```

`extends:` lists the docs it will change. The rsvp doc itself stays as it is until this is built. `## Changes to <target>` is what gets merged then.

---

## docs/changes/<change>.md

```markdown
---
type: change
status: planned
changes: [features/rsvp]
---

# Close replies a day before the dinner

Hosts need a final headcount for the restaurant.

## Now
- Replies close when the dinner starts.

## After
- Replies close 24 hours before the dinner starts.
- The dinner page says "Replies close tomorrow at 19:00"
  during the last day before closing.

## Acceptance criteria
- Given a dinner starting in 23 hours, when a guest
  replies, then they see "Replies are closed."
```

Name the file after the change, not a date or number. When built, the `## After` lines are written into the target docs, and the change doc gets `status: done` with a first line `Merged into [[features/rsvp]].`

---

## docs/pages/<page>.md

```markdown
---
type: page
uses: [features/rsvp, components/guest-list]
---

# <Page name>

<Who comes here and what they come to do.>

## Who can open it
- Anyone with the invite link.

## What's on it
1. Dinner name, date, place and the host's note.
2. Reply buttons: Going, Maybe, Can't go.
3. Seats left, e.g. "4 of 10 seats left".
4. Who's coming, as a [[components/guest-list]].
5. After the dinner starts: "Replies are closed."

## Actions
- Reply → [[features/rsvp]]

## Look and feel *(optional)*
- The reply buttons stay visible while scrolling on phones.
```

Describe layout as an ordered list from top to bottom, not as coordinates or CSS.

---

## docs/components/<component>.md

```markdown
---
type: component
shown-on: [pages/dinner, pages/my-dinners]
uses: [data/rsvp]
---

# <Component name>

<What it shows, in one sentence.>

## Shows
- Guests who are going, then maybe, each with their name and note
- A count at the top: "6 going, 2 maybe"

## Variants *(optional)*
- Compact: names only, used on the host's list of dinners.
```

---

## docs/integrations/<service>.md

```markdown
---
type: integration
---

# <Email / Sign-in / Payments …>

<What the app uses this for.>

## New reply
<a name="new-reply"></a>
- **When**: a guest replies or changes their reply.
- **To**: the host.
- **Says**: who replied, their answer and their note.

## Reminder
- **When**: the day before the dinner.
- **To**: guests who said going or maybe.

## Limits *(optional)*
- At most one reply email per guest per hour; later changes are batched.
```

Give each event or message its own heading so features can link to it with `#anchor`.

---

## docs/.tech/stack.md

```markdown
---
type: tech
---

# Stack

- Runtime: Node 22, Hono
- Data: SQLite, one file
- UI: server-rendered HTML + htmx
- Tests: Vitest, one test file per feature doc, named after it

## Mapping *(optional)*
- data/rsvp → table `rsvps`
- features/rsvp → `src/features/rsvp.ts`
```

`.tech/` is for whoever reads code. Keep it terse. The mapping section helps you find the code for a doc quickly; keep it updated when you create files.
