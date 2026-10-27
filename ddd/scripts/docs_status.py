#!/usr/bin/env python3
"""Track changes to a doc-driven project's docs/ folder.

Commands
  status         What changed in docs/ since the last apply, what it affects, broken links,
                 and planned changes whose target doc was edited after they were written.
  diff PATH      Line diff of one doc against its last applied version.
  mark-applied   Record the current docs as built (all, or only the paths given).
  restore PATH   Put one doc back to its last applied version.
  roadmap        Progress per phase in docs/roadmap.md, mismatches with feature status.
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
PLAN_STATUSES = ("idea", "planned", "in-progress")
STATUSES = PLAN_STATUSES + ("done",)
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


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_state(spec):
    f = spec / STATE_FILE
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def parse_refs(text):
    """Docs this doc points at: frontmatter uses/shown-on plus [[wiki links]]."""
    refs = set()
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm, key = text[3:end], None
            for line in fm.splitlines():
                m = re.match(r"^([\w-]+):\s*(.*)$", line)
                if m:
                    key, val = m.group(1), m.group(2).strip()
                    if key in REL_KEYS and val.startswith("["):
                        refs.update(v.strip().strip("'\"") for v in val.strip("[]").split(",") if v.strip())
                elif key in REL_KEYS and line.strip().startswith("- "):
                    refs.add(line.strip()[2:].strip().strip("'\""))
    refs.update(m.group(1).strip() for m in LINK_RE.finditer(text))
    return {r.removesuffix(".md") for r in refs if r}


def frontmatter(text):
    """Simple key: value pairs from the frontmatter (lists are left as raw text)."""
    out = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                m = re.match(r"^([\w-]+):\s*(.*)$", line)
                if m:
                    out[m.group(1)] = m.group(2).strip().strip("'\"")
    return out


def fm_list(text, key):
    """A list value from the frontmatter: `key: [a, b]` or a `- a` block."""
    if not text.startswith("---"):
        return []
    end = text.find("\n---", 3)
    if end == -1:
        return []
    out, cur = [], None
    for line in text[3:end].splitlines():
        m = re.match(r"^([\w-]+):\s*(.*)$", line)
        if m:
            cur, val = m.group(1), m.group(2).strip()
            if cur == key and val:
                vals = val.strip("[]").split(",") if val.startswith("[") else [val]
                out += [v.strip().strip("'\"") for v in vals if v.strip()]
        elif cur == key and line.strip().startswith("- "):
            out.append(line.strip()[2:].strip().strip("'\""))
    return [v.removesuffix(".md") for v in out]


def plan_targets(path):
    """Docs a planned extension or change will modify when it's built."""
    text = path.read_text(encoding="utf-8")
    return sorted({t for k in TARGET_KEYS for t in fm_list(text, k)})


def doc_status(path):
    """Feature status from frontmatter, or None for docs that don't track one."""
    st = frontmatter(path.read_text(encoding="utf-8")).get("status", "").lower()
    return st or None


def build_graph(docs):
    out = {d: parse_refs(p.read_text(encoding="utf-8")) for d, p in docs.items()}
    back = {d: set() for d in docs}
    for d, refs in out.items():
        for r in refs:
            back.setdefault(r, set()).add(d)
    return out, back


def compute(root):
    spec = spec_dir(root)
    docs = list_docs(spec)
    state = load_state(spec)
    current = {d: sha(p.read_text(encoding="utf-8")) for d, p in docs.items()}
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
            text = docs[d].read_text(encoding="utf-8")
            hit |= {r for r in parse_refs(text) if r.startswith("pages/")}
        hit -= touched
        if hit:
            impact[d] = sorted(hit)
    broken = sorted({(d, r) for d, refs in out.items() for r in refs if r not in docs})
    baselines = (state or {}).get("baselines", {})
    stale = []
    for d, p in docs.items():
        if doc_status(p) not in PLAN_STATUSES:
            continue
        for t, h in baselines.get(d, {}).items():
            if t in current and current[t] != h:
                stale.append({"plan": d, "target": t})
    plan_only = sorted(d for d in set(added) | set(changed)
                       if d == ROADMAP or doc_status(docs[d]) in PLAN_STATUSES)
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
            print("Plan only (not built yet, no code to change):")
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


def resolve(spec, path):
    p = Path(path)
    if p.suffix != ".md":
        p = p.with_suffix(".md")
    parts = p.parts
    if "docs" in parts:
        p = Path(*parts[parts.index("docs") + 1:])
    return p.as_posix()


def cmd_diff(args):
    spec = spec_dir(args.root)
    rel = resolve(spec, args.path)
    now = spec / rel
    old = spec / STATE_DIR / rel
    a = old.read_text(encoding="utf-8").splitlines() if old.exists() else []
    b = now.read_text(encoding="utf-8").splitlines() if now.exists() else []
    if not old.exists() and not now.exists():
        sys.exit(f"{rel}: not found now or at last apply.")
    lines = list(difflib.unified_diff(a, b, f"applied/{rel}", f"current/{rel}", lineterm="", n=2))
    print("\n".join(lines) if lines else f"{rel}: unchanged since last apply.")


def cmd_mark(args):
    spec = spec_dir(args.root)
    docs = list_docs(spec)
    state = load_state(spec) or {"docs": {}}
    if args.paths:
        targets = {Path(resolve(spec, p)).with_suffix("").as_posix() for p in args.paths}
    else:
        targets = set(docs) | set(state["docs"])
    snap = spec / STATE_DIR
    explicit = bool(args.paths)
    current = {d: sha(p.read_text(encoding="utf-8")) for d, p in docs.items()}
    baselines = state.setdefault("baselines", {})
    for d in sorted(targets):
        rel = d + ".md"
        if d in docs:
            before = state["docs"].get(d)
            tg = plan_targets(docs[d]) if doc_status(docs[d]) in PLAN_STATUSES else []
            if tg:
                # Record which version of each target this plan was written against.
                # Refreshed when the plan itself was edited (re-reviewed) or named explicitly.
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
    rel = resolve(spec, args.path)
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
    for line in f.read_text(encoding="utf-8").splitlines():
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
    statuses = {d: doc_status(p) for d, p in docs.items()}
    issues, listed, nxt = [], set(), None
    for ph in phases:
        for it in ph["items"]:
            d = it["doc"]
            if d:
                listed.add(d)
                if d not in docs:
                    issues.append(f"{d}: on the roadmap but no such doc")
                    it["status"] = None
                    continue
                st = it["status"] = statuses[d]
                if it["checked"] and st != "done":
                    issues.append(f"{d}: checked on the roadmap but status is {st or 'missing'}")
                if not it["checked"] and st == "done":
                    issues.append(f"{d}: status is done but not checked on the roadmap")
            else:
                it["status"] = "done" if it["checked"] else None
    for ph in phases:  # an item already in progress comes first
        for it in ph["items"]:
            if it.get("status") == "in-progress" and not it["checked"]:
                nxt = nxt or dict(it, phase=ph["title"])
    for ph in phases:
        if not ph["scheduled"]:
            continue
        for it in ph["items"]:
            if not it["checked"]:
                nxt = nxt or dict(it, phase=ph["title"])
    for d, st in sorted(statuses.items()):
        if st and st not in STATUSES:
            issues.append(f"{d}: unknown status '{st}' (use {', '.join(STATUSES)})")
        if st in ("planned", "in-progress") and d not in listed:
            issues.append(f"{d}: status is {st} but it is not on the roadmap")
    return {"phases": phases, "next": nxt, "issues": issues}


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
            st = f" ({it['status']})" if it["doc"] and it.get("status") not in (None, "done") else ""
            print(f"  [{mark}] {label}{st}")
    nx = r["next"]
    print(f"Next: {(nx['doc'] or nx['text'])} ({nx['phase']})" if nx else "Next: nothing left in scheduled phases.")
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
        print("Nothing left in scheduled phases.")
    else:
        where = f"docs/{nx['doc']}.md" if nx["doc"] else "(task with no doc)"
        st = nx.get("status") or "not started"
        print(f"{nx['phase']}: {nx['doc'] or nx['text']}\n  {where}, status: {st}")


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
    # allow --root after the subcommand too
    for p in (s, d, m, r, rm, n):
        p.add_argument("--root", default=argparse.SUPPRESS)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
