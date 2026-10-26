#!/usr/bin/env python3
"""Rebuild the PR tables in README.md from GitHub.

Each repo in REPOS gets its own block in the README, between:
    <!-- PRS:owner/repo:START -->
    <!-- PRS:owner/repo:END -->

Custom descriptions live in scripts/pr_titles.json. A PR without one
shows its GitHub title.
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

AUTHOR = "BADERFPV"
REPOS = [
    "betaflight/betaflight-configurator",
        "betaflight/betaflight",
    "ExpressLRS/ExpressLRS-Configurator",
]
SHOW_CLOSED_UNMERGED = False

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
TITLES = ROOT / "scripts" / "pr_titles.json"

BADGES = {
    "merged": "![](https://img.shields.io/badge/merged-8250df)",
    "open": "![](https://img.shields.io/badge/open-2ea44f)",
    "draft": "![](https://img.shields.io/badge/draft-6e7681)",
    "closed": "![](https://img.shields.io/badge/closed-cf222e)",
}


def fetch_prs(repo):
    query = f"is:pr author:{AUTHOR} repo:{repo}"
    url = "https://api.github.com/search/issues?" + urllib.parse.urlencode(
        {"q": query, "per_page": 100, "sort": "created", "order": "desc"}
    )
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["items"]


def status_of(pr):
    if pr.get("pull_request", {}).get("merged_at"):
        return "merged"
    if pr["state"] == "closed":
        return "closed"
    if pr.get("draft"):
        return "draft"
    return "open"


def build_table(repo, prs, titles):
    rows = []
    for pr in sorted(prs, key=lambda p: p["number"], reverse=True):
        status = status_of(pr)
        if status == "closed" and not SHOW_CLOSED_UNMERGED:
            continue
        num = pr["number"]
        text = titles.get(repo, {}).get(str(num), pr["title"])
        text = text.replace("|", "\\|")
        link = f"[#{num}](https://github.com/{repo}/pull/{num})"
        rows.append(f"| {link} | {text} | {BADGES[status]} |")
    if not rows:
        return ""
    head = "| PR | Change | Status |\n| --- | --- | --- |"
    return head + "\n" + "\n".join(rows)


def replace_block(readme, repo, table):
    start = f"<!-- PRS:{repo}:START -->"
    end = f"<!-- PRS:{repo}:END -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(readme):
        return readme
    body = f"{start}\n{table}\n{end}" if table else f"{start}\n{end}"
    return pattern.sub(lambda _: body, readme)


def main():
    titles = json.loads(TITLES.read_text(encoding="utf-8")) if TITLES.exists() else {}
    readme = README.read_text(encoding="utf-8")
    new = readme
    for repo in REPOS:
        if f"<!-- PRS:{repo}:START -->" not in new:
            continue
        prs = fetch_prs(repo)
        new = replace_block(new, repo, build_table(repo, prs, titles))
    if new != readme:
        README.write_text(new, encoding="utf-8")
        print("README updated")
    else:
        print("No changes")


if __name__ == "__main__":
    sys.exit(main())
