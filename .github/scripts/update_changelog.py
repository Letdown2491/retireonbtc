#!/usr/bin/env python3
import subprocess, re, os
from datetime import datetime, timedelta
from dateutil.parser import parse as dtparse

CHANGELOG = "CHANGELOG.md"

# Matches the exact paragraph you called out (with or without backticks around YYYY-MM-DD)
ANCHOR_RE = re.compile(
    r"This project loosely follows the spirit of Keep a Changelog and Semantic Versioning\. "
    r"Dates use `?YYYY-MM-DD`?\. "
    r"No formal version tags have been created yet; entries are grouped by date\.",
    re.M,
)

DATE_H2_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$", re.M)
CONV_RE = re.compile(r"^(feat|fix|perf|docs|test|ci|build|refactor|chore)(?:\([\w\/\-\._]+\))?:\s*(.+)$", re.I)

SECTION_ORDER = [
    "Added", "Fixed", "Performance", "Changed", "Docs", "Tests", "CI", "Build", "Refactor", "Chore"
]

def git(*args) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()

def latest_date_from_changelog():
    if not os.path.exists(CHANGELOG):
        return None
    with open(CHANGELOG, "r", encoding="utf-8") as f:
        m = DATE_H2_RE.search(f.read())
    return dtparse(m.group(1)).date() if m else None

def commits_since(date_):
    args = ["log", "--date=short", "--pretty=%H%x09%ad%x09%an%x09%s", "--no-merges"]
    if date_:
        # Start from the next day to avoid re-listing the last recorded date
        since = (datetime.combine(date_, datetime.min.time()) + timedelta(days=1)).strftime("%Y-%m-%d")
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

def bucketize(commits):
    days = {}
    for c in commits:
        day = c["date"]
        subj = c["subject"].strip()
        m = CONV_RE.match(subj)
        if m:
            kind = m.group(1).lower()
            msg = m.group(2).strip()
            mapping = {
                "feat": "Added", "fix": "Fixed", "perf": "Performance", "docs": "Docs",
                "test": "Tests", "ci": "CI", "build": "Build", "refactor": "Refactor", "chore": "Chore"
            }
            section = mapping.get(kind, "Changed")
        else:
            msg = subj
            section = "Changed"
        days.setdefault(day, {}).setdefault(section, []).append(f"- {msg}")
    return days

def render_sections(day_sections: dict) -> str:
    out = []
    for section in SECTION_ORDER:
        items = day_sections.get(section)
        if not items:
            continue
        out.append(f"### {section}\n" + "\n".join(items) + "\n")
    return ("\n".join(out)).rstrip() + "\n"

def insert_entries(entries_markdown: str):
    with open(CHANGELOG, "r", encoding="utf-8") as f:
        content = f.read()

    m = ANCHOR_RE.search(content)
    if m:
        # Insert RIGHT AFTER the anchor paragraph
        insert_pos = m.end()
        # keep exactly two newlines after the anchor paragraph before inserting
        # (normalize any number of newlines that may already exist)
        tail = content[insert_pos:]
        # strip leading newlines in tail; we’ll add exactly two back
        tail = tail.lstrip("\n")
        new_content = content[:insert_pos] + "\n\n" + entries_markdown + tail
    else:
        # Fallback: insert before the first dated section (keeps newest at top)
        first_date = DATE_H2_RE.search(content)
        if first_date:
            new_content = content[:first_date.start()] + entries_markdown + content[first_date.start():]
        else:
            # Last resort: append to end
            new_content = content.rstrip() + "\n\n" + entries_markdown

    if new_content != content:
        with open(CHANGELOG, "w", encoding="utf-8") as f:
            f.write(new_content)

def main():
    if not os.path.exists(CHANGELOG):
        raise SystemExit(f"{CHANGELOG} not found. Commit your CHANGELOG first.")

    last_date = latest_date_from_changelog()
    commits = commits_since(last_date)
    if not commits:
        print("No new commits to add to changelog.")
        return

    buckets = bucketize(commits)
    dates_desc = sorted(buckets.keys(), reverse=True)
    sections = []
    for d in dates_desc:
        sections.append(f"## {d}\n\n{render_sections(buckets[d])}\n")
    insert_entries("".join(sections))

if __name__ == "__main__":
    main()
