#!/usr/bin/env python3
# .github/scripts/update_changelog.py
# Requires: pip install gitpython python-dateutil

import os
import re
from collections import OrderedDict
from datetime import datetime, timezone
from dateutil.parser import parse as dtparse
from git import Repo

CHANGELOG = "CHANGELOG.md"

# Anchor: insert new dated sections immediately after this paragraph
ANCHOR_RE = re.compile(
    r"This project loosely follows the spirit of Keep a Changelog and Semantic Versioning\. "
    r"Dates use `?YYYY-MM-DD`?\. "
    r"No formal version tags have been created yet; entries are grouped by date\.",
    re.M,
)

# Find dated sections like: ## 2025-08-24
DATE_H2_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$", re.M)
DATE_HDR_RE_FMT = r"^##\s+{date}\s*$"  # used to slice out an existing date section

# Conventional Commit mapping (classification uses the SUBJECT only)
CONV_RE = re.compile(r"^(feat|fix|perf|docs|test|ci|build|refactor|chore)(?:\([\w\/\-\._]+\))?:\s*(.+)$", re.I)
SECTION_ORDER = ["Added", "Fixed", "Performance", "Changed", "Docs", "Tests", "CI", "Build", "Refactor", "Chore"]

# Common trailer lines to ignore in body parsing
TRAILER_RE = re.compile(r"^(co-authored-by|signed-off-by|see-?also|refs?|fixes|breaking change)\b", re.I)

repo = Repo(".")

def topmost_changelog_date():
    """Return the date of the first dated section in CHANGELOG.md, or None."""
    if not os.path.exists(CHANGELOG):
        return None
    with open(CHANGELOG, "r", encoding="utf-8") as f:
        content = f.read()
    m = DATE_H2_RE.search(content)
    return dtparse(m.group(1)).date() if m else None

def _strip_trailers(body: str) -> str:
    """Cut off the body at the first trailer-style line (Co-authored-by, Signed-off-by, Fixes, etc.)."""
    if not body:
        return ""
    lines = body.splitlines()
    kept = []
    for ln in lines:
        if TRAILER_RE.match(ln.strip()):
            break
        kept.append(ln)
    return "\n".join(kept).rstrip()

def _first_paragraph(body: str) -> str | None:
    """
    Return the first full paragraph from the commit body:
    - Trim leading blank lines
    - Paragraph = consecutive non-empty lines up to a blank line
    - Normalize internal whitespace and strip list markers per line
    - Ignore if the paragraph is empty after normalization
    """
    if not body:
        return None

    body = _strip_trailers(body)

    # Split into paragraphs by blank lines while preserving order
    para = []
    got_any = False
    for raw in body.splitlines():
        line = raw.rstrip()
        if line.strip() == "":
            if para:
                got_any = True
                break
            else:
                continue
        para.append(line)

    # If we never hit a blank line but still collected lines, that's our paragraph
    if not got_any and not para:
        return None

    # Normalize: remove list markers at paragraph line starts and collapse spaces
    cleaned_lines = []
    for ln in para:
        # strip common bullet prefixes
        ln = re.sub(r"^\s*([-*•]|\d+\.)\s+", "", ln)
        ln = re.sub(r"\s+", " ", ln).strip()
        if ln:
            cleaned_lines.append(ln)

    display = " ".join(cleaned_lines).strip()
    return display or None

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

        # Subject (title) and body (description)
        full = c.message or ""
        lines = full.splitlines()
        subject = (lines[0] if lines else "").strip()
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

        # Use committer datetime for stable YYYY-MM-DD grouping
        day = c.committed_datetime.strftime("%Y-%m-%d")

        commits.append({
            "sha": c.hexsha,
            "date": day,
            "author": author_name,
            "subject": subject,
            "body": body
        })
    return commits

def bucketize_by_date(commits):
    """
    Returns:
      {
        'YYYY-MM-DD': {
          'Added': OrderedDict({<lower display>: <original display>, ...}),
          'Changed': OrderedDict(...),
          ...
        }
      }
    Dedupe by the final displayed text (case-insensitive) within each section/day.
    Classification uses the subject (title) to detect Conventional Commit type.
    """
    days: dict[str, dict[str, OrderedDict[str, str]]]= {}
    mapping = {
        "feat": "Added", "fix": "Fixed", "perf": "Performance", "docs": "Docs",
        "test": "Tests", "ci": "CI", "build": "Build", "refactor": "Refactor", "chore": "Chore"
    }

    for c in commits:
        day = c["date"]
        subject = c["subject"].strip()
        body = c["body"]

        # Prefer first full paragraph of description; else subject; else fallback
        display = _first_paragraph(body) or subject or "(no message)"

        # Section from Conventional Commit kind (based on subject), else "Changed"
        m = CONV_RE.match(subject)
        if m:
            kind = m.group(1).lower()
            section = mapping.get(kind, "Changed")
        else:
            section = "Changed"

        key = display.lower()  # normalized for dedupe
        sec = days.setdefault(day, {}).setdefault(section, OrderedDict())
        if key not in sec:
            sec[key] = display  # keep original casing/text

    return days

def render_day_sections(day_sections: dict) -> str:
    parts = []
    for section in SECTION_ORDER:
        od = day_sections.get(section)
        if not od:
            continue
        lines = [f"- {original}" for original in od.values()]
        parts.append(f"### {section}\n" + "\n".join(lines) + "\n")
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
    # Remove existing sections for any dates we’re about to (re)write
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
    dates_desc = sorted(buckets.keys(), reverse=True)

    # Render new sections (newest first)
    new_block_md = "".join(
        f"## {d}\n\n{render_day_sections(buckets[d])}\n" for d in dates_desc
    )

    # Load file, remove any existing sections for these dates, and insert under anchor paragraph
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
