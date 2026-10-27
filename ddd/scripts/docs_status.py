#!/usr/bin/env python3
"""Track changes to a doc-driven project's docs/ folder.

Commands
  status         What changed in docs/ since the last apply, what it affects, broken links.
  diff PATH      Line diff of one doc against its last applied version.
  mark-applied   Record the current docs as built (all, or only the paths given).
  restore PATH   Put one doc back to its last applied version.

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
REL_KEYS = ("uses", "shown-on")


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
    return {
        "initialized": state is not None,
        "added": added, "changed": changed, "removed": removed,
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
        for label, key in (("Added", "added"), ("Changed", "changed"), ("Removed", "removed")):
            if r[key]:
                print(f"{label}:")
                for d in r[key]:
                    print(f"  {d}")
        if r["impact"]:
            print("May be affected:")
            for d, hits in r["impact"].items():
                print(f"  {d} -> {', '.join(hits)}")
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
    for d in sorted(targets):
        rel = d + ".md"
        if d in docs:
            state["docs"][d] = sha(docs[d].read_text(encoding="utf-8"))
            (snap / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(docs[d], snap / rel)
        else:
            state["docs"].pop(d, None)
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="project root (the folder that holds docs/)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_status)
    d = sub.add_parser("diff"); d.add_argument("path"); d.set_defaults(fn=cmd_diff)
    m = sub.add_parser("mark-applied"); m.add_argument("paths", nargs="*"); m.set_defaults(fn=cmd_mark)
    r = sub.add_parser("restore"); r.add_argument("path"); r.set_defaults(fn=cmd_restore)
    # allow --root after the subcommand too
    for p in (s, d, m, r):
        p.add_argument("--root", default=argparse.SUPPRESS)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
