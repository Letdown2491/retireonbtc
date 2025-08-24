#!/usr/bin/env python3
import os, re
from datetime import datetime, timezone
from dateutil.parser import parse as dtparse
from git import Repo

CHANGELOG = "CHANGELOG.md"

# Your anchor paragraph (with or without backticks around YYYY-MM-DD)
ANCHOR_RE = re.compile(
    r"This project loosely follows the spirit of Keep a Changelog and Semantic Versioning\. "
    r"Dates use `?YYYY-MM-DD`?\. "
    r"No formal version tags have been created yet; entries are grouped by date\.",
    re.M,
)

# Find dated sections like: ## 2025-08-24
DATE_H2_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$", re.M)
DATE_HDR_RE_FMT = r"^##\s+{date}\s*$"  # used to slice out an existing date section

# Conventional Commit mapping
CONV_RE = re.compile(r"^(feat|fix|perf|docs|test|ci|build|refactor|chore)(?:\([\w\/\-\._]+\))?:\s*(.+)$", re.I)
SECTION_ORDER = ["Added", "Fixed", "Performance", "Changed", "Docs", "Tests", "CI", "Build", "Refactor", "Chore"]

repo = Repo(".")

def topmost_changelog_date():
    if not os.path.exists(CHANGELOG):
        return None
    with open(CHANGELOG, "r", encoding="utf-8") as f:
        content = f.read()
    m = DATE_H2_RE.search(content)
    return dtparse(m.group(1)).date() if m else None

def commits_since_including(date_):
    """
    Return all non-merge commits from <date_ 00:00Z> to HEAD, inclusive.
    We rebuild the top day every run to capture additional same-day merges.
    """
    if date_:
        since_dt = datetime.combine(date_, datetime.min.time()).replace(tzinfo=timezone.utc)
        it = repo.iter_commits("HEAD", no_merges=True, since=since_dt.isoformat())
    else:
        it = repo.iter_commits("HEAD", no_merges=True)

    commits = []
    for c in it:
        author_name = (c.author.name or "")
        if author_name.lower().startswith("github-actions[bot]"):
            continue
        subject = (c.message.splitlines()[0] or "").strip()
        # Use committer datetime's own timezone for stable YYYY-MM-DD grouping
        day = c.committed_datetime.strftime("%Y-%m-%d")
        commits.append({"sha": c.hexsha, "date": day, "author": author_name, "subject": subject})
    return commits

def bucketize_by_date(commits):
    """
    { 'YYYY-MM-DD': { 'Added': ['- msg', ...], 'Fixed': [...], ... } }
    """
    days = {}
    for c in commits:
        day = c["date"]
        subj = c["subject"]
        m = CONV_RE.match(subj)
        if m:
            kind = m.group(1).lower()
            msg = m.group(2).strip()
            mapping = {
                "feat":"Added", "fix":"Fixed", "perf":"Performance", "docs":"Docs",
                "test":"Tests", "ci":"CI", "build":"Build", "refactor":"Refactor", "chore":"Chore"
            }
            section = mapping.get(kind, "Changed")
        else:
            msg = subj
            section = "Changed"
        days.setdefault(day, {}).setdefault(section, []).append(f"- {msg}")
    return days

def render_day_sections(day_sections: dict) -> str:
    parts = []
    for section in SECTION_ORDER:
        items = day_sections.get(section)
        if not items:
            continue
        parts.append(f"### {section}\n" + "\n".join(items) + "\n")
    return "\n".join(parts).rstrip() + "\n"

def find_anchor_end(content: str) -> int:
    m = ANCHOR_RE.search(content)
    if not m:
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
    spans = []
    for d in dates:
        span = find_section_span(content, d)
        if span:
            spans.append(span)
    # Remove bottom-up to preserve indices
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
    dates_desc = sorted(buckets.keys(), reverse=True)

    # Render new sections (newest first)
    new_block = []
    for d in dates_desc:
        new_block.append(f"## {d}\n\n{render_day_sections(buckets[d])}\n")
    new_block_md = "".join(new_block)

    # Load current content, remove existing sections for the dates we will replace,
    # and insert the rebuilt block immediately after the anchor paragraph.
    with open(CHANGELOG, "r", encoding="utf-8") as f:
        content = f.read()

    content = remove_sections_for_dates(content, dates_desc)

    anchor_end = find_anchor_end(content)
    head = content[:anchor_end]
    tail = content[anchor_end:].lstrip("\n")  # normalize spacing
    updated = head + "\n\n" + new_block_md + tail

    if updated != content:
        with open(CHANGELOG, "w", encoding="utf-8") as f:
            f.write(updated)
        print("CHANGELOG.md updated.")
    else:
        print("No changes to CHANGELOG.md.")

if __name__ == "__main__":
    main()
