# Doc templates

One template per doc type. Copy the shape, not the example content. Sections marked *(optional)* can be dropped when empty; everything else stays, even if short.

Contents: app.md · data · features · pages · components · integrations · .tech

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
| Employee | Requests leave, sees their balance |
| Manager | Approves or rejects their team's requests |
| Admin | Manages people and holidays |

## What it does
- [[features/submit-request]]
- [[features/approve-request]]

## Glossary
- **Balance**: days of leave a person has left this year.
- **Working day**: Monday to Friday, excluding public holidays.

## Out of scope *(optional)*
- Payroll, expenses.
```

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
| requester | [[data/person]] asking for leave | yes |
| start, end | first and last day off, inclusive | yes |
| status | pending, approved, rejected, cancelled | yes |

## Rules *(optional)*
- End is on or after start.

## Who can see it *(optional)*
- The requester, their manager, admins.
```

Field names are written as people say them, not as column names. `.tech/` maps them to code if needed.

---

## docs/features/<feature>.md

```markdown
---
type: feature
uses: [data/leave-request, data/person, integrations/email]
shown-on: [pages/my-requests, pages/team-calendar]
---

# <Verb phrase: "Approve a leave request">

<One or two sentences: what happens and why it matters.>

## Who
- Only the requester's [[data/person#manager]] can decide.

## Rules
- A request can only be decided while it is **pending**.
- Rejecting requires a reason.

## States *(optional, when something moves through stages)*
pending → approved
pending → rejected

## What happens after *(optional)*
- Requester gets an email: [[integrations/email#decision]]

## Acceptance criteria
- Given a pending request, when the manager approves it,
  then its status is approved and the balance drops.
- Given a rejection with no reason, then it is blocked
  with "add a reason".

## Open questions *(optional)*
- Can managers approve their own requests?
```

---

## docs/pages/<page>.md

```markdown
---
type: page
uses: [features/approve-request, components/request-card]
---

# <Page name>

<Who comes here and what they come to do.>

## Who can open it
- Managers and admins.

## What's on it
1. A list of pending requests from the manager's team, oldest first,
   each shown as a [[components/request-card]].
2. Approve and Reject buttons on each card.
3. An empty state: "Nothing to review."

## Actions
- Approve → [[features/approve-request]]

## Look and feel *(optional)*
- Pending requests older than 3 days are highlighted.
```

Describe layout as an ordered list from top to bottom, not as coordinates or CSS.

---

## docs/components/<component>.md

```markdown
---
type: component
shown-on: [pages/my-requests, pages/team-calendar]
uses: [data/leave-request]
---

# <Component name>

<What it shows, in one sentence.>

## Shows
- Requester name and photo
- Dates and number of working days
- Status as a coloured label: pending (grey), approved (green), rejected (red)

## Variants *(optional)*
- Compact: name and dates only, used on the calendar.
```

---

## docs/integrations/<service>.md

```markdown
---
type: integration
---

# <Email / Auth / Payments …>

<What the app uses this for.>

## Decision
<a name="decision"></a>
- **When**: a request is approved or rejected.
- **To**: the requester.
- **Says**: the decision, the dates, and the manager's reason if any.

## Limits *(optional)*
- No more than one email per request per day.
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
- data/leave-request → table `leave_requests`
- features/approve-request → `src/features/approve-request.ts`
```

`.tech/` is for whoever reads code. Keep it terse. The mapping section helps you find the code for a doc quickly; keep it updated when you create files.
