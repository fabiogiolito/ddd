#!/usr/bin/env python3
"""Track changes to a doc-driven project's docs/ folder.

Where a doc lives says what stage it is in:
  docs/plan/ideas/   loose ideas, not committed
  docs/plan/         committed, not built yet (status: planned or in-progress)
  docs/plan/done/    plans that were built and merged, kept as a record
  everywhere else    built: describes the app as it is

Commands
  status         What changed in docs/ since the last apply, what it affects, broken links,
                 and plans whose target doc was edited after they were written.
  diff PATH      Line diff of one doc against its last applied version.
  mark-applied   Record the current docs as built (all, or only the paths given).
  restore PATH   Put one doc back to its last applied version.
  roadmap        Progress per phase in docs/roadmap.md, and anything out of sync.
  next           The next roadmap item to work on.

State lives inside docs/: .state.json (a hash per doc) and .state/ (a copy of each
doc as last applied). Both should be committed with the project if it uses git.
Standard library only.
"""
import argparse
import difflib
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

STATE_FILE = ".state.json"
STATE_DIR = ".state"
LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
REL_KEYS = ("uses", "shown-on", "extends", "changes")
TARGET_KEYS = ("extends", "changes")
PLAN_STATUSES = ("planned", "in-progress")
ROADMAP = "roadmap"
UNSCHEDULED = ("ideas", "backlog")
ITEM_RE = re.compile(r"^\s*[-*]\s+\[( |x|X)\]\s+(.*)$")


def spec_dir(root):
    d = Path(root).resolve() / "docs"
    if not d.is_dir():
        sys.exit(f"No docs/ folder under {Path(root).resolve()}. Is this a doc-driven project?")
    return d


def doc_id(spec, path):
    """docs/features/x.md -> features/x"""
    return path.relative_to(spec).with_suffix("").as_posix()


def list_docs(spec):
    docs = {}
    for p in sorted(spec.rglob("*.md")):
        rel = p.relative_to(spec)
        if rel.parts[0] == STATE_DIR:
            continue
        docs[doc_id(spec, p)] = p
    return docs


def stage(d):
    """idea | plan | record | built | roadmap, from where the doc lives."""
    if d == ROADMAP:
        return "roadmap"
    if d.startswith("plan/ideas/"):
        return "idea"
    if d.startswith("plan/done/"):
        return "record"
    if d.startswith("plan/"):
        return "plan"
    return "built"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_state(spec):
    f = spec / STATE_FILE
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def read(p):
    return p.read_text(encoding="utf-8")


def frontmatter_block(text):
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end != -1 else ""


def fm_value(text, key):
    for line in frontmatter_block(text).splitlines():
        m = re.match(r"^([\w-]+):\s*(.*)$", line)
        if m and m.group(1) == key:
            return m.group(2).strip().strip("'\"")
    return ""


def fm_list(text, key):
    """A list value from the frontmatter: `key: [a, b]`, `key: a` or a `- a` block."""
    out, cur = [], None
    for line in frontmatter_block(text).splitlines():
        m = re.match(r"^([\w-]+):\s*(.*)$", line)
        if m:
            cur, val = m.group(1), m.group(2).strip()
            if cur == key and val:
                vals = val.strip("[]").split(",") if val.startswith("[") else [val]
                out += [v.strip().strip("'\"") for v in vals if v.strip()]
        elif cur == key and line.strip().startswith("- "):
            out.append(line.strip()[2:].strip().strip("'\""))
    return [v.removesuffix(".md") for v in out]


def parse_refs(text):
    """Docs this doc points at: frontmatter relationships plus [[wiki links]]."""
    refs = {r for k in REL_KEYS for r in fm_list(text, k)}
    refs.update(m.group(1).strip() for m in LINK_RE.finditer(text))
    return {r.removesuffix(".md") for r in refs if r}


def plan_targets(text):
    return sorted({t for k in TARGET_KEYS for t in fm_list(text, k)})


def build_graph(docs):
    out = {d: parse_refs(read(p)) for d, p in docs.items()}
    back = {d: set() for d in docs}
    for d, refs in out.items():
        for r in refs:
            back.setdefault(r, set()).add(d)
    return out, back


def compute(root):
    spec = spec_dir(root)
    docs = list_docs(spec)
    state = load_state(spec)
    current = {d: sha(read(p)) for d, p in docs.items()}
    applied = (state or {}).get("docs", {})
    added = sorted(set(current) - set(applied))
    removed = sorted(set(applied) - set(current))
    changed = sorted(d for d in current if d in applied and current[d] != applied[d])
    out, back = build_graph(docs)
    touched = set(added) | set(removed) | set(changed)
    impact = {}
    for d in sorted(touched):
        hit = set(back.get(d, set()))
        if d in out:  # pages a component or feature is shown on are affected too
            hit |= {r for r in out[d] if r.startswith("pages/")}
        hit -= touched
        if hit:
            impact[d] = sorted(hit)
    broken = sorted({(d, r) for d, refs in out.items() for r in refs if r not in docs})
    # Edits to plans, ideas, records and the roadmap need no code change.
    plan_only = sorted(d for d in set(added) | set(changed) | set(removed) if stage(d) != "built")
    baselines = (state or {}).get("baselines", {})
    stale = []
    for d in docs:
        if stage(d) not in ("plan", "idea"):
            continue
        for t, h in baselines.get(d, {}).items():
            if t in current and current[t] != h:
                stale.append({"plan": d, "target": t})
    return {
        "initialized": state is not None,
        "added": added, "changed": changed, "removed": removed,
        "plan_only": plan_only,
        "stale_plans": stale,
        "impact": impact,
        "broken_links": [{"in": d, "to": r} for d, r in broken],
        "doc_count": len(docs),
    }


def cmd_status(args):
    r = compute(args.root)
    if args.json:
        print(json.dumps(r, indent=2))
        return
    if not r["initialized"]:
        print(f"Never applied: {r['doc_count']} docs, no build recorded yet.")
        print("Build from the docs, then run mark-applied.")
    elif not (r["added"] or r["changed"] or r["removed"]):
        print(f"No changes since last apply ({r['doc_count']} docs).")
    else:
        plan = set(r["plan_only"])
        for label, key in (("Added", "added"), ("Changed", "changed"), ("Removed", "removed")):
            items = [d for d in r[key] if d not in plan]
            if items:
                print(f"{label}:")
                for d in items:
                    print(f"  {d}")
        if plan:
            print("Plan only (not built, no code to change):")
            for d in r["plan_only"]:
                print(f"  {d}")
        if r["impact"]:
            print("May be affected:")
            for d, hits in r["impact"].items():
                print(f"  {d} -> {', '.join(hits)}")
    if r["stale_plans"]:
        print("Plans to re-check (the doc they change was edited after they were written):")
        for x in r["stale_plans"]:
            print(f"  {x['plan']} -> {x['target']}")
    if r["broken_links"]:
        print("Broken links:")
        for b in r["broken_links"]:
            print(f"  {b['in']} -> [[{b['to']}]] (no such doc)")


def resolve(path):
    p = Path(path)
    if p.suffix != ".md":
        p = p.with_suffix(".md")
    parts = p.parts
    if "docs" in parts:
        p = Path(*parts[parts.index("docs") + 1:])
    return p.as_posix()


def cmd_diff(args):
    spec = spec_dir(args.root)
    rel = resolve(args.path)
    now = spec / rel
    old = spec / STATE_DIR / rel
    if not old.exists() and not now.exists():
        sys.exit(f"{rel}: not found now or at last apply.")
    a = old.read_text(encoding="utf-8").splitlines() if old.exists() else []
    b = now.read_text(encoding="utf-8").splitlines() if now.exists() else []
    lines = list(difflib.unified_diff(a, b, f"applied/{rel}", f"current/{rel}", lineterm="", n=2))
    print("\n".join(lines) if lines else f"{rel}: unchanged since last apply.")


def cmd_mark(args):
    spec = spec_dir(args.root)
    docs = list_docs(spec)
    state = load_state(spec) or {"docs": {}}
    explicit = bool(args.paths)
    if explicit:
        targets = {Path(resolve(p)).with_suffix("").as_posix() for p in args.paths}
    else:
        targets = set(docs) | set(state["docs"])
    current = {d: sha(read(p)) for d, p in docs.items()}
    baselines = state.setdefault("baselines", {})
    snap = spec / STATE_DIR
    for d in sorted(targets):
        rel = d + ".md"
        if d in docs:
            before = state["docs"].get(d)
            tg = plan_targets(read(docs[d])) if stage(d) in ("plan", "idea") else []
            if tg:
                # Which version of each target this plan was written against. Refreshed
                # when the plan itself was edited (re-checked) or named explicitly.
                if explicit or before != current[d] or d not in baselines:
                    baselines[d] = {t: current[t] for t in tg if t in current}
            else:
                baselines.pop(d, None)
            state["docs"][d] = current[d]
            (snap / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(docs[d], snap / rel)
        else:
            state["docs"].pop(d, None)
            baselines.pop(d, None)
            (snap / rel).unlink(missing_ok=True)
    (spec / STATE_FILE).write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Marked {len(targets)} doc(s) as applied.")


def cmd_restore(args):
    spec = spec_dir(args.root)
    rel = resolve(args.path)
    old = spec / STATE_DIR / rel
    if not old.exists():
        sys.exit(f"{rel}: no applied version to restore (it is new since the last apply).")
    (spec / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(old, spec / rel)
    print(f"Restored {rel} to its last applied version.")


def parse_roadmap(spec):
    f = spec / (ROADMAP + ".md")
    if not f.exists():
        return None
    phases, cur = [], None
    for line in read(f).splitlines():
        h = re.match(r"^##\s+(.*)$", line)
        if h:
            title = h.group(1).strip()
            cur = {"title": title, "items": [],
                   "scheduled": not title.lower().startswith(UNSCHEDULED)}
            phases.append(cur)
            continue
        m = ITEM_RE.match(line)
        if m and cur is not None:
            text = m.group(2).strip()
            link = LINK_RE.search(text)
            cur["items"].append({"checked": m.group(1) != " ", "text": text,
                                 "doc": link.group(1).strip() if link else None})
    return phases


def roadmap_report(root):
    spec = spec_dir(root)
    docs = list_docs(spec)
    phases = parse_roadmap(spec)
    if phases is None:
        return None
    issues, listed, nxt = [], set(), None
    for ph in phases:
        for it in ph["items"]:
            d = it["doc"]
            if not d:
                it["status"] = "done" if it["checked"] else "not started"
                continue
            listed.add(d)
            if d not in docs:
                issues.append(f"{d}: on the roadmap but no such doc (moved? update the link)")
                it["status"] = None
                continue
            st = stage(d)
            if st == "plan":
                it["status"] = fm_value(read(docs[d]), "status") or "planned"
                if it["checked"]:
                    issues.append(f"{d}: checked on the roadmap but still in plan/ "
                                  "(move it to features/, or merge it and move it to plan/done/)")
            elif st == "idea":
                it["status"] = "idea"
                issues.append(f"{d}: an idea is on the roadmap; move it to plan/ to commit to it")
            else:  # built or record
                it["status"] = "done"
                if not it["checked"]:
                    issues.append(f"{d}: built, but not checked on the roadmap")
    for ph in phases:  # an item already in progress comes first
        for it in ph["items"]:
            if it.get("status") == "in-progress" and not it["checked"]:
                nxt = nxt or dict(it, phase=ph["title"])
    for ph in phases:
        if not ph["scheduled"]:
            continue
        for it in ph["items"]:
            if not it["checked"] and it.get("status") != "idea":
                nxt = nxt or dict(it, phase=ph["title"])
    for d, p in sorted(docs.items()):
        st, val = stage(d), fm_value(read(p), "status")
        if st == "plan":
            if val and val not in PLAN_STATUSES:
                issues.append(f"{d}: unknown status '{val}' (use {' or '.join(PLAN_STATUSES)})")
            if d not in listed:
                issues.append(f"{d}: in plan/ but not on the roadmap (add it, or move it to plan/ideas/)")
        elif st == "built" and val:
            issues.append(f"{d}: built docs don't carry a status; remove 'status: {val}'")
    ideas = sum(1 for d in docs if stage(d) == "idea")
    return {"phases": phases, "next": nxt, "issues": issues, "ideas": ideas}


def cmd_roadmap(args):
    r = roadmap_report(args.root)
    if r is None:
        sys.exit("No docs/roadmap.md yet.")
    if args.json:
        print(json.dumps(r, indent=2))
        return
    for ph in r["phases"]:
        items = ph["items"]
        if not items:
            continue
        done = sum(1 for it in items if it["checked"])
        tail = f"{done}/{len(items)} done" if ph["scheduled"] else f"{len(items)} unscheduled"
        print(f"{ph['title']}: {tail}")
        for it in items:
            mark = "x" if it["checked"] else ("~" if it.get("status") == "in-progress" else " ")
            label = it["doc"] or it["text"]
            st = it.get("status")
            note = f" ({st})" if it["doc"] and st not in (None, "done", "planned") else ""
            print(f"  [{mark}] {label}{note}")
    if r["ideas"]:
        print(f"Ideas in plan/ideas/: {r['ideas']}")
    nx = r["next"]
    print(f"Next: {(nx['doc'] or nx['text'])} ({nx['phase']})" if nx else "Next: nothing left on the roadmap.")
    if r["issues"]:
        print("Out of sync:")
        for i in r["issues"]:
            print(f"  {i}")


def cmd_next(args):
    r = roadmap_report(args.root)
    if r is None:
        sys.exit("No docs/roadmap.md yet.")
    nx = r["next"]
    if args.json:
        print(json.dumps(nx, indent=2))
    elif not nx:
        print("Nothing left on the roadmap.")
    else:
        where = f"docs/{nx['doc']}.md" if nx["doc"] else "(task with no doc)"
        print(f"{nx['phase']}: {nx['doc'] or nx['text']}\n  {where}, status: {nx.get('status')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="project root (the folder that holds docs/)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_status)
    d = sub.add_parser("diff"); d.add_argument("path"); d.set_defaults(fn=cmd_diff)
    m = sub.add_parser("mark-applied"); m.add_argument("paths", nargs="*"); m.set_defaults(fn=cmd_mark)
    r = sub.add_parser("restore"); r.add_argument("path"); r.set_defaults(fn=cmd_restore)
    rm = sub.add_parser("roadmap"); rm.add_argument("--json", action="store_true"); rm.set_defaults(fn=cmd_roadmap)
    n = sub.add_parser("next"); n.add_argument("--json", action="store_true"); n.set_defaults(fn=cmd_next)
    for p in (s, d, m, r, rm, n):  # allow --root after the subcommand too
        p.add_argument("--root", default=argparse.SUPPRESS)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
