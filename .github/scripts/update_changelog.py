#!/usr/bin/env python3
import subprocess, re, os
from datetime import datetime, timedelta
from dateutil.parser import parse as dtparse

CHANGELOG = "CHANGELOG.md"

ANCHOR_RE = re.compile(
    r"This project loosely follows the spirit of Keep a Changelog and Semantic Versioning\. "
    r"Dates use `?YYYY-MM-DD`?\. "
    r"No formal version tags have been created yet; entries are grouped by date\.",
    re.M,
)
DATE_H2_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$", re.M)
DATE_HDR_RE_FMT = r"^##\s+{date}\s*$"  # filled with re.escape(date)
CONV_RE = re.compile(r"^(feat|fix|perf|docs|test|ci|build|refactor|chore)(?:\([\w\/\-\._]+\))?:\s*(.+)$", re.I)

SECTION_ORDER = ["Added", "Fixed", "Performance", "Changed", "Docs", "Tests", "CI", "Build", "Refactor", "Chore"]

def git(*args) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()

def topmost_changelog_date():
    if not os.path.exists(CHANGELOG):
        return None
    with open(CHANGELOG, "r", encoding="utf-8") as f:
        content = f.read()
    m = DATE_H2_RE.search(content)
    return dtparse(m.group(1)).date() if m else None

def commits_since_including(date_):
    """Return all non-merge commits from <date_ 00:00> to HEAD, inclusive."""
    args = ["log", "--date=short", "--pretty=%H%x09%ad%x09%an%x09%s", "--no-merges"]
    if date_:
        since = datetime.combine(date_, datetime.min.time()).strftime("%Y-%m-%d")
        args.append(f"--since={since}")
    out = git(*args)
    commits = []
    if out:
        for line in out.splitlines():
            sha, d, author, subj = line.split("\t", 3)
            if author.lower().startswith("github-actions[bot]"):
                continue
            commits.append({"sha": sha, "date": d, "author": author, "subject": subj})
    return commits

def bucketize_by_date(commits):
    days = {}
    for c in commits:
        day = c["date"]
        subj = c["subject"].strip()
        m = CONV_RE.match(subj)
        if m:
            kind = m.group(1).lower()
            msg = m.group(2).strip()
            mapping = {
                "feat":"Added","fix":"Fixed","perf":"Performance","docs":"Docs",
                "test":"Tests","ci":"CI","build":"Build","refactor":"Refactor","chore":"Chore"
            }
            section = mapping.get(kind, "Changed")
        else:
            msg = subj
            section = "Changed"
        days.setdefault(day, {}).setdefault(section, []).append(f"- {msg}")
    return days

def render_day_sections(day_sections: dict) -> str:
    out = []
    for section in SECTION_ORDER:
        items = day_sections.get(section)
        if not items:
            continue
        out.append(f"### {section}\n" + "\n".join(items) + "\n")
    return "\n".join(out).rstrip() + "\n"

def find_anchor_end(content: str) -> int:
    m = ANCHOR_RE.search(content)
    if not m:
        # fallback to beginning of first date section
        fd = DATE_H2_RE.search(content)
        return fd.start() if fd else len(content)
    return m.end()

def find_section_span(content: str, date_str: str):
    hdr_re = re.compile(DATE_HDR_RE_FMT.format(date=re.escape(date_str)), re.M)
    m = hdr_re.search(content)
    if not m:
        return None
    next_m = DATE_H2_RE.search(content, m.end())
    end = next_m.start() if next_m else len(content)
    return (m.start(), end)

def remove_sections_for_dates(content: str, dates: list[str]) -> str:
    # Remove from the bottom up to keep indices valid
    spans = []
    for d in dates:
        span = find_section_span(content, d)
        if span:
            spans.append(span)
    for start, end in sorted(spans, key=lambda x: x[0], reverse=True):
        content = content[:start] + content[end:]
    return content

def main():
    if not os.path.exists(CHANGELOG):
        raise SystemExit(f"{CHANGELOG} not found. Commit your CHANGELOG first.")

    top_date = topmost_changelog_date()
    commits = commits_since_including(top_date)
    if not commits:
        print("No new commits to add to changelog.")
        return

    buckets = bucketize_by_date(commits)
    # Build sections for all dates >= top_date (if top_date exists) or for all new dates if file had none
    dates_desc = sorted(buckets.keys(), reverse=True)

    # Render markdown block for these dates (newest first)
    new_block = []
    for d in dates_desc:
        new_block.append(f"## {d}\n\n{render_day_sections(buckets[d])}\n")
    new_block_md = "".join(new_block)

    # Load, remove existing sections for these dates (so we can replace top_date and avoid duplicates)
    with open(CHANGELOG, "r", encoding="utf-8") as f:
        content = f.read()

    content = remove_sections_for_dates(content, dates_desc)

    # Insert right after the anchor paragraph (normalize spacing to exactly two newlines after it)
    anchor_end = find_anchor_end(content)
    head = content[:anchor_end]
    tail = content[anchor_end:]
    tail = tail.lstrip("\n")  # normalize
    updated = head + "\n\n" + new_block_md + tail

    if updated != content:
        with open(CHANGELOG, "w", encoding="utf-8") as f:
            f.write(updated)
        print("CHANGELOG.md updated.")
    else:
        print("No changes to CHANGELOG.md.")

if __name__ == "__main__":
    main()
