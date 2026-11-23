#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""The subject-tree memory, as files on disk, with every file read and write counted.

    uv run memory_tree.py scale [--sizes 10 100 1000] [--out DIR] [--report FILE]
    uv run memory_tree.py check MEMORY_DIR

`scale` plays n synthetic chats through the same rules the discussion-memory skill
gives Claude (one file per level on recall, one branch rewritten on save, a branch
over 1,200 tokens splits, at most 30 headings per index, depth at most 3) and
reports what a chat costs in tokens at each n.

`check` validates a real memory/ folder (one written by Claude in a session)
against the same limits.

Tokens are counted as 4 characters per token, rounded up.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import math
import pathlib
import random
import re
import shutil
import sys
from dataclasses import dataclass, field

MAX_HEADINGS = 30
MAX_TOKENS = 1200          # any index, any branch file
MAX_DEPTH = 3              # files opened per recall, after the loaded root index
MAX_SETTINGS_TOKENS = 300
LINE_CHARS = 150           # one index line
ENTRY_HEAD = "## "
MOVED = "Moved to "

INDEX_LINE = re.compile(r"^\s*[-*]\s+\*\*(?P<heading>.+?)\*\*.*?`(?P<target>[^`]+\.md)`(?P<rest>.*)$")


def tokens(text: str) -> int:
    return math.ceil(len(text) / 4)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "subject"


def stable(text: str, mod: int) -> int:
    return int(hashlib.sha1(text.encode()).hexdigest(), 16) % mod


# --------------------------------------------------------------------------- files

@dataclass
class Op:
    """What one step (load, recall, save) touched."""
    kind: str
    reads: list = field(default_factory=list)    # (relative path, tokens)
    writes: list = field(default_factory=list)

    @property
    def read_tokens(self) -> int:
        return sum(t for _, t in self.reads)


class Store:
    """All file access goes through here so it can be counted."""

    def __init__(self, root: pathlib.Path):
        self.root = pathlib.Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.op: Op | None = None

    def begin(self, kind: str) -> Op:
        self.op = Op(kind)
        return self.op

    def read(self, rel: str) -> str:
        text = (self.root / rel).read_text(encoding="utf-8")
        if self.op is not None:
            self.op.reads.append((rel, tokens(text)))
        return text

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        if self.op is not None:
            self.op.writes.append((rel, tokens(text)))

    def exists(self, rel: str) -> bool:
        return (self.root / rel).is_file()


# --------------------------------------------------------------------------- index and branch text

def parse_index(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        m = INDEX_LINE.match(line)
        if m:
            rest = m.group("rest")
            gist = rest.split("|")[1].strip() if rest.count("|") >= 1 else ""
            last = re.search(r"last (\d{4}-\d{2}-\d{2})", rest)
            rows.append({"heading": m.group("heading"), "target": m.group("target"),
                         "gist": gist, "last": last.group(1) if last else ""})
    return rows


def render_index(title: str, rows: list[dict]) -> str:
    lines = [f"# {title}"]
    for r in rows:
        head = f"- **{r['heading']}** → `{r['target']}` | "
        tail = f" | last {r['last']}"
        room = max(0, LINE_CHARS - len(head) - len(tail))
        lines.append(head + r["gist"][:room].rstrip() + tail)
    return "\n".join(lines) + "\n"


def parse_branch(text: str) -> list[dict]:
    """Entries of a branch file: [{'title', 'body'}], in file order."""
    entries, cur = [], None
    for line in text.splitlines():
        if line.startswith(ENTRY_HEAD):
            cur = {"title": line[len(ENTRY_HEAD):].strip(), "body": []}
            entries.append(cur)
        elif cur is not None and line.strip():
            cur["body"].append(line)
    return entries


def render_branch(entries: list[dict]) -> str:
    out = []
    for e in entries:
        out.append(ENTRY_HEAD + e["title"])
        out.extend(e["body"])
        out.append("")
    return "\n".join(out)


def entry_last(e: dict) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", " ".join(e["body"]))
    return m.group(1) if m else ""


def entry_labels(e: dict) -> list[str]:
    for line in e["body"]:
        if line.startswith("- Filed under:"):
            return [s.strip() for s in line.split(":", 1)[1].split(">")]
    return []


# --------------------------------------------------------------------------- the tree

@dataclass
class Subject:
    labels: list[str]   # broad -> narrow, e.g. ["Bronze Age Europe", "Bell Beaker", "aDNA"]
    title: str


class MemoryTree:
    def __init__(self, root: pathlib.Path):
        self.s = Store(root)
        if not self.s.exists("INDEX.md"):
            self.s.write("INDEX.md", "# Subjects\n")

    # -- session start: the one thing always loaded
    def load(self) -> Op:
        op = self.s.begin("load")
        self.s.read("INDEX.md")
        return op

    def _pick(self, rows: list[dict], label: str) -> dict | None:
        for r in rows:
            if r["heading"] == label:
                return r
        return None

    def _walk(self, subject: Subject, root_text: str):
        """Follow one branch from the root index down to the leaf holding this subject.
        Opens one file per level. Returns (chain, leaf_rel, leaf_text) where chain is
        [(index_rel, rows, row)] from the root down; leaf_rel is None when the subject's
        heading does not exist yet."""
        chain = []
        index_rel, rows = "INDEX.md", parse_index(root_text)
        for depth in range(1, MAX_DEPTH + 1):
            label = subject.labels[depth - 1]
            row = self._pick(rows, label)
            if row is None and len(rows) >= MAX_HEADINGS:
                row = rows[stable(label, len(rows))]       # index full: closest existing heading
            if row is None:
                chain.append((index_rel, rows, None))
                return chain, None, None
            chain.append((index_rel, rows, row))
            base = str(pathlib.PurePosixPath(index_rel).parent)
            rel = row["target"] if base == "." else f"{base}/{row['target']}"
            text = self.s.read(rel)
            if rel.endswith("INDEX.md") and depth < MAX_DEPTH:
                index_rel, rows = rel, parse_index(text)
                continue
            return chain, rel, text
        raise AssertionError("tree deeper than MAX_DEPTH")

    # -- recall: one file per level
    def recall(self, subject: Subject, root_text: str) -> tuple[Op, dict | None]:
        op = self.s.begin("recall")
        chain, leaf_rel, leaf_text = self._walk(subject, root_text)
        found = None
        if leaf_text is not None:
            for e in parse_branch(leaf_text):
                if e["title"] == subject.title:
                    found = e
        return op, found

    # -- save: rewrite one branch, update the index line it hangs from
    def save(self, subject: Subject, body: list[str], today: str, root_text: str) -> Op:
        op = self.s.begin("save")
        chain, leaf_rel, leaf_text = self._walk(subject, root_text)
        index_rel, rows, row = chain[-1]
        base = str(pathlib.PurePosixPath(index_rel).parent)
        depth = len(chain)
        if leaf_rel is None:                                # new heading in this index
            label = subject.labels[depth - 1]
            row = {"heading": label, "target": f"{slug(label)}.md", "gist": "", "last": today}
            rows.append(row)
            leaf_rel = row["target"] if base == "." else f"{base}/{row['target']}"
            entries = []
        else:
            entries = parse_branch(leaf_text)
        entry = {"title": subject.title,
                 "body": body + ["- Filed under: " + " > ".join(subject.labels)]}
        for i, e in enumerate(entries):
            if e["title"] == subject.title:
                entries[i] = entry
                break
        else:
            entries.append(entry)
        row["last"] = today
        row["gist"] = "; ".join(e["title"] for e in sorted(entries, key=entry_last, reverse=True))
        self._write_leaf(leaf_rel, entries, depth, row, base)
        title = "Subjects" if index_rel == "INDEX.md" else chain[-2][2]["heading"]
        self.s.write(index_rel, render_index(title, rows))
        return op

    def _write_leaf(self, rel: str, entries: list[dict], depth: int, row: dict, base: str) -> None:
        text = render_branch(entries)
        if tokens(text) <= MAX_TOKENS:
            self.s.write(rel, text)
            return
        if depth >= MAX_DEPTH:                              # deepest level: shorten the oldest
            order = sorted(range(len(entries)), key=lambda i: entry_last(entries[i]))
            for i in order:
                if tokens(render_branch(entries)) <= MAX_TOKENS:
                    break
                e = entries[i]
                keep = [l for l in e["body"] if l.startswith(("- Last discussed", "- Filed under"))]
                entries[i] = {"title": e["title"], "body": keep}
            while tokens(render_branch(entries)) > MAX_TOKENS:   # still over: retire the oldest
                entries.pop(min(range(len(entries)), key=lambda i: entry_last(entries[i])))
            self.s.write(rel, render_branch(entries))
            return
        # split into sub-headings by the next, narrower label
        groups: dict[str, list[dict]] = {}
        for e in entries:
            labels = entry_labels(e)
            label = labels[depth] if len(labels) > depth else "Other"
            if label not in groups and len(groups) >= MAX_HEADINGS:
                label = list(groups)[stable(label, len(groups))]
            groups.setdefault(label, []).append(e)
        folder = rel[:-3]                                   # bell-beaker.md -> bell-beaker/
        sub_rows = []
        for label, group in groups.items():
            sub_row = {"heading": label, "target": f"{slug(label)}.md",
                       "gist": "; ".join(e["title"] for e in group),
                       "last": max(entry_last(e) for e in group)}
            sub_rows.append(sub_row)
            self._write_leaf(f"{folder}/{sub_row['target']}", group, depth + 1, sub_row, folder)
        self.s.write(f"{folder}/INDEX.md", render_index(row["heading"], sub_rows))
        self.s.write(rel, f"{MOVED}{pathlib.PurePosixPath(folder).name}/INDEX.md\n")
        row["target"] = row["target"][:-3] + "/INDEX.md"


# --------------------------------------------------------------------------- checking a folder on disk

def check_folder(memory_dir: pathlib.Path) -> tuple[dict, list[str]]:
    """Validate a memory/ folder. Returns (measurements, problems)."""
    memory_dir = pathlib.Path(memory_dir)
    problems: list[str] = []
    stats = {"loaded_tokens": 0, "headings": 0, "max_file_tokens": 0, "max_depth": 0,
             "files": 0, "total_tokens": 0, "settings_tokens": None}
    root = memory_dir / "INDEX.md"
    if not root.is_file():
        return stats, ["no INDEX.md"]
    reachable = {root.resolve()}

    def visit(index_path: pathlib.Path, depth: int):
        text = index_path.read_text(encoding="utf-8")
        rows = parse_index(text)
        name = str(index_path.relative_to(memory_dir))
        if len(rows) > MAX_HEADINGS:
            problems.append(f"{name}: {len(rows)} headings (limit {MAX_HEADINGS})")
        if tokens(text) > MAX_TOKENS:
            problems.append(f"{name}: {tokens(text)} tokens (limit {MAX_TOKENS})")
        for r in rows:
            target = index_path.parent / r["target"]
            if not target.is_file():
                problems.append(f"{name}: heading '{r['heading']}' points to a missing file {r['target']}")
                continue
            reachable.add(target.resolve())
            stats["max_depth"] = max(stats["max_depth"], depth)
            if target.name == "INDEX.md":
                if depth >= MAX_DEPTH:
                    problems.append(f"{name}: '{r['heading']}' goes deeper than {MAX_DEPTH} levels")
                else:
                    visit(target, depth + 1)
            else:
                t = tokens(target.read_text(encoding="utf-8"))
                if t > MAX_TOKENS:
                    problems.append(f"{target.relative_to(memory_dir)}: {t} tokens (limit {MAX_TOKENS})")
        return rows

    rows = visit(root, 1)
    stats["headings"] = len(rows)
    stats["loaded_tokens"] = tokens(root.read_text(encoding="utf-8"))
    for p in sorted(memory_dir.rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        if p.name == "SETTINGS.md" and p.parent == memory_dir:
            stats["settings_tokens"] = tokens(text)
            if tokens(text) > MAX_SETTINGS_TOKENS:
                problems.append(f"SETTINGS.md: {tokens(text)} tokens (limit {MAX_SETTINGS_TOKENS})")
            continue
        stats["files"] += 1
        stats["total_tokens"] += tokens(text)
        stats["max_file_tokens"] = max(stats["max_file_tokens"], tokens(text))
        if p.resolve() not in reachable and not text.startswith(MOVED) and text.strip():
            problems.append(f"{p.relative_to(memory_dir)}: not reachable from any index")
    return stats, problems


# --------------------------------------------------------------------------- synthetic chats

AREAS = [
    "Bell Beaker phenomenon", "Neolithic transition", "Bronze Age collapse", "Roman frontier",
    "Maya urbanism", "Andean states", "Mississippian mounds", "Indus cities", "Jomon pottery",
    "Lapita expansion", "Great Zimbabwe", "Nile Valley predynastic", "Mesopotamian urbanism",
    "Aegean palaces", "Iron Age hillforts", "Viking towns", "Silk Road sites", "Clovis and pre-Clovis",
    "Australian rock art", "Gobekli Tepe", "Stonehenge landscape", "Shang bronzes", "Angkor hydraulics",
    "Swahili coast", "Scythian kurgans", "Etruscan tombs", "Hallstatt salt", "Cahokia",
    "Chaco roads", "Olmec heads", "Catalhoyuk houses", "Natufian burials", "Yamnaya herders",
    "Linearbandkeramik", "Cucuteni megasites", "Nabataean trade", "Aksum stelae", "Moche ceramics",
    "Polynesian voyaging", "Medieval deserted villages",
]
METHODS = ["radiocarbon chronology", "ancient DNA", "isotope analysis", "ceramic typology",
           "lithic analysis", "zooarchaeology", "archaeobotany", "remote sensing", "settlement survey",
           "burial practice"]
DEBATES = ["migration versus diffusion", "dating of the earliest phase", "elite control", "climate as cause",
           "sample size", "diet and subsistence", "trade networks", "ritual or domestic", ]
STANCES = ["the evidence is too thin to carry the claim", "the sample is biased toward elite burials",
           "the chronology cannot separate cause from effect", "a local development explains it as well",
           "the method was applied outside its range", "the regional pattern does not hold site by site"]


def synthetic_body(rng: random.Random, today: str, earlier: list[str], area: str, method: str) -> list[str]:
    last = f"- Last discussed: {today}" + (f" (before: {', '.join(earlier[-2:])})" if earlier else "")
    year = rng.randint(1995, 2026)
    doi = f"10.{rng.randint(1000, 9999)}/{slug(area)[:8]}.{rng.randint(100, 999)}"
    return [
        last,
        f"- His position: on {area}, {rng.choice(STANCES)}; he wants {method} checked against stratigraphy.",
        f"- My position: {rng.choice(STANCES)}, though the {method} results are consistent across sites.",
        f"- Articles: Author{rng.randint(1, 400)} et al. {year} ({doi})",
        f"- Open angles: compare with {rng.choice(AREAS)}; ask whether {rng.choice(DEBATES)} changes the reading.",
    ]


def simulate(n: int, out_dir: pathlib.Path, seed: int = 7, p_new: float = 0.5) -> dict:
    """Play n chats. Each chat: load the root index, recall its subject, save it."""
    if out_dir.exists():
        shutil.rmtree(out_dir)
    rng = random.Random(seed)
    tree = MemoryTree(out_dir)
    subjects: list[Subject] = []
    history: dict[str, list[str]] = {}
    weights = [1 / (i + 1) for i in range(len(AREAS))]          # a few areas dominate, as in real use
    day = dt.date(2026, 1, 5)
    m = {"n": n, "loaded_max": 0, "recall_level_max": 0, "recall_total_max": 0, "depth_max": 0,
         "recall_files_max": 0, "save_reads_max": 0, "save_writes_max": 0, "save_writes_sum": 0,
         "recalled": 0, "recall_misses": 0}
    for i in range(n):
        day += dt.timedelta(days=rng.choice([0, 1, 1, 2, 3]))
        today = day.isoformat()
        revisit = bool(subjects) and rng.random() >= p_new
        if revisit:
            subject = subjects[int(len(subjects) * (1 - rng.random() ** 2)) - 1]   # recent ones more often
        else:
            area = rng.choices(AREAS, weights)[0]
            method, debate = rng.choice(METHODS), rng.choice(DEBATES)
            subject = Subject([area, method, debate], f"{area}: {debate} ({method}) #{len(subjects) + 1}")
            subjects.append(subject)
        op = tree.load()
        root_text = (out_dir / "INDEX.md").read_text(encoding="utf-8")
        m["loaded_max"] = max(m["loaded_max"], op.read_tokens)
        if revisit:
            op, found = tree.recall(subject, root_text)
            m["recalled"] += 1
            m["recall_misses"] += found is None
            m["recall_files_max"] = max(m["recall_files_max"], len(op.reads))
            m["depth_max"] = max(m["depth_max"], len(op.reads))
            m["recall_total_max"] = max(m["recall_total_max"], op.read_tokens)
            m["recall_level_max"] = max([m["recall_level_max"]] + [t for _, t in op.reads])
        earlier = history.setdefault(subject.title, [])
        op = tree.save(subject, synthetic_body(rng, today, earlier, subject.labels[0], subject.labels[1]),
                       today, root_text)
        earlier.append(today)
        m["save_reads_max"] = max(m["save_reads_max"], len(op.reads))
        m["save_writes_max"] = max(m["save_writes_max"], len(op.writes))
        m["save_writes_sum"] += len(op.writes)
        m["depth_max"] = max(m["depth_max"], len(op.reads))
    stats, problems = check_folder(out_dir)
    m.update(subjects=len(subjects), files=stats["files"], total_tokens=stats["total_tokens"],
             headings=stats["headings"], loaded_final=stats["loaded_tokens"],
             max_file_tokens=stats["max_file_tokens"], disk_depth=stats["max_depth"],
             problems=problems, save_writes_mean=m["save_writes_sum"] / n)
    return m


def verdict(m: dict) -> list[str]:
    fails = []
    if m["loaded_max"] > MAX_TOKENS:
        fails.append(f"n={m['n']}: loaded {m['loaded_max']} tokens > {MAX_TOKENS}")
    if m["recall_level_max"] > MAX_TOKENS:
        fails.append(f"n={m['n']}: a recall level read {m['recall_level_max']} tokens > {MAX_TOKENS}")
    if m["depth_max"] > MAX_DEPTH:
        fails.append(f"n={m['n']}: depth {m['depth_max']} > {MAX_DEPTH}")
    if m["headings"] > MAX_HEADINGS:
        fails.append(f"n={m['n']}: {m['headings']} root headings > {MAX_HEADINGS}")
    if m["max_file_tokens"] > MAX_TOKENS:
        fails.append(f"n={m['n']}: a file holds {m['max_file_tokens']} tokens > {MAX_TOKENS}")
    if m["recall_misses"]:
        fails.append(f"n={m['n']}: {m['recall_misses']} revisited subjects were not found by the one-branch walk")
    fails += [f"n={m['n']}: {p}" for p in m["problems"]]
    return fails


def report(results: list[dict], fails: list[str]) -> str:
    def row(label, key, fmt="{:,}"):
        return f"| {label} | " + " | ".join(fmt.format(r[key]) for r in results) + " |"
    head = "| | " + " | ".join(f"n = {r['n']:,}" for r in results) + " |"
    sep = "|---|" + "---:|" * len(results)
    lines = [
        "# Scaling report: subject-tree memory",
        "",
        "Produced by `uv run phase-3-discussion-memory/scaling/memory_tree.py scale`. n = number of chats.",
        "Each synthetic chat loads the root index, recalls its subject if it has come up before, and saves.",
        "Tokens = characters / 4, rounded up. Numbers are the worst case seen over all n chats, measured on the files written to disk.",
        "",
        "## Against the limits",
        "",
        head, sep,
        row(f"Tokens loaded at the start of a chat (limit {MAX_TOKENS:,})", "loaded_max"),
        row(f"Tokens read per recall, largest single level (limit {MAX_TOKENS:,})", "recall_level_max"),
        row(f"Depth: files opened per recall (limit {MAX_DEPTH})", "depth_max"),
        row("Tokens read per recall, all levels together", "recall_total_max"),
        row(f"Root headings (limit {MAX_HEADINGS})", "headings"),
        "",
        "## What a step touches, against what exists",
        "",
        head, sep,
        row("Subjects remembered", "subjects"),
        row("Files in memory/", "files"),
        row("Tokens in memory/, all files", "total_tokens"),
        row("Files read by one recall, most", "recall_files_max"),
        row("Files read by one save, most", "save_reads_max"),
        row("Files written by one save, most (a split)", "save_writes_max"),
        row("Files written by one save, mean", "save_writes_mean", "{:.2f}"),
        row("Revisited subjects found by the one-branch walk", "recalled"),
        row("Revisited subjects missed", "recall_misses"),
        "",
        "No step lists or reads the whole folder: the most files any recall or save read is in the table, while the folder holds the file count above it.",
        "",
        "## Result",
        "",
        ("**PASS**: every limit holds at every n." if not fails else "**FAIL**:\n" + "\n".join(f"- {f}" for f in fails)),
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    here = pathlib.Path(__file__).resolve().parent
    sc = sub.add_parser("scale")
    sc.add_argument("--sizes", type=int, nargs="+", default=[10, 100, 1000])
    sc.add_argument("--out", type=pathlib.Path, default=here / "out")
    sc.add_argument("--report", type=pathlib.Path, default=here / "REPORT.md")
    sc.add_argument("--seed", type=int, default=7)
    ck = sub.add_parser("check")
    ck.add_argument("memory_dir", type=pathlib.Path)
    args = ap.parse_args(argv)

    if args.cmd == "check":
        stats, problems = check_folder(args.memory_dir)
        for k, v in stats.items():
            print(f"{k}: {v}")
        for p in problems:
            print("FAIL:", p)
        print("RESULT:", "FAIL" if problems else "PASS")
        return 1 if problems else 0

    results = [simulate(n, args.out / f"n{n}", seed=args.seed) for n in args.sizes]
    fails = [f for r in results for f in verdict(r)]
    text = report(results, fails)
    args.report.write_text(text, encoding="utf-8")
    print(text)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
