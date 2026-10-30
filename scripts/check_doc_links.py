"""Offline check for ordinary relative Markdown links and heading fragments."""
from collections import Counter
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

LINK = re.compile(r"!?\[[^\]\n]*\]\(([^\s)]+)(?:\s+[^)]*)?\)")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")


def visible_lines(text):
    fence = None
    for line in text.splitlines():
        match = FENCE.match(line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            yield line


def heading_ids(text):
    counts = Counter()
    result = set()
    for line in visible_lines(text):
        match = HEADING.match(line)
        if not match:
            continue
        name = match.group(1).lower()
        name = "".join(c for c in name if c.isalnum() or c in "_- ")
        name = name.replace(" ", "-")
        suffix = counts[name]
        counts[name] += 1
        result.add(name if suffix == 0 else f"{name}-{suffix}")
    return result


def check(root):
    root = Path(root).resolve()
    issues = []
    for source in sorted(root.rglob("*.md")):
        if any(part in {".git", ".venv", "node_modules"} for part in source.relative_to(root).parts):
            continue
        text = source.read_text(encoding="utf-8")
        for line in visible_lines(text):
            for match in LINK.finditer(line):
                target = match.group(1)
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc:
                    continue  # External links are deliberately not fetched.
                destination = (source.parent / unquote(parsed.path)).resolve() if parsed.path else source
                label = source.relative_to(root)
                if not destination.is_relative_to(root):
                    issues.append(f"{label}: link leaves repository: {target}")
                elif not destination.exists():
                    issues.append(f"{label}: missing target: {target}")
                elif parsed.fragment and destination.is_file() and destination.suffix.lower() == ".md":
                    if unquote(parsed.fragment) not in heading_ids(destination.read_text(encoding="utf-8")):
                        issues.append(f"{label}: missing heading: {target}")
    return issues


if __name__ == "__main__":
    problems = check(Path(__file__).resolve().parents[1])
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit(1)
    print("Relative Markdown paths and supported heading fragments are valid.")
