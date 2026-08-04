#!/usr/bin/env python3
"""Post an AI review onto the pull request, inline on the changed lines.

The reviewer emits JSON. Left as a build artifact, nobody reads it. This puts
each finding on the line it refers to, and turns the reviewer's suggested code
into a GitHub suggestion block so it can be applied with one click.

    python3 post_review.py review.json --pr 1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

API = "https://api.github.com"

# Anything the reviewer flags at or above this level is worth interrupting for.
# Lower findings still post; this only controls the summary's framing.
URGENT = {"critical", "high"}


def dedupe(comments: list[dict]) -> list[dict]:
    """The reviewer repeats itself: 15 comments over 12 unique locations in one
    measured run. Posting duplicates would put two review threads on one line."""
    seen: set[tuple[str, int]] = set()
    out: list[dict] = []
    for c in comments:
        key = (c.get("path", ""), c.get("start_line", 0))
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def body_for(finding: dict) -> str:
    severity = str(finding.get("severity", "unknown")).lower()
    category = str(finding.get("category", "")).strip()
    label = f"**{severity.upper()}**" + (f" · {category}" if category else "")
    parts = [f"{label}", "", str(finding.get("content", "")).strip()]

    suggestion = str(finding.get("suggestion_code", "") or "").strip()
    if suggestion:
        # A ```suggestion block renders as an applicable patch in the PR UI.
        parts += ["", "```suggestion", suggestion, "```"]
    return "\n".join(parts)


def summary_for(findings: list[dict], data: dict) -> str:
    s = data.get("summary", {})
    urgent = sum(1 for f in findings
                 if str(f.get("severity", "")).lower() in URGENT)
    head = (f"**{len(findings)} finding(s)**, {urgent} needing attention before merge."
            if findings else "**No findings** on the changed lines.")
    return "\n".join([
        "## AI code review",
        "",
        head,
        "",
        f"Reviewed {s.get('files_reviewed', 0)} file(s) in "
        f"{s.get('elapsed', 'unknown')} using {s.get('total_tokens', 0):,} tokens.",
        "",
        "This review is advisory and does not block the merge. Measured against "
        "a labelled set of known problems it found between 26.7% and 80% of "
        "them across identical runs, so a clean review means nothing was found, "
        "not that nothing is wrong. A human still reviews this change.",
    ])


def post(repo: str, pr: int, token: str, findings: list[dict], summary: str) -> None:
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github+json"}
    comments = [{"path": f["path"], "line": f.get("end_line") or f["start_line"],
                 "side": "RIGHT", "body": body_for(f)}
                for f in findings if f.get("path") and f.get("start_line")]

    r = requests.post(f"{API}/repos/{repo}/pulls/{pr}/reviews", headers=headers,
                      json={"body": summary, "event": "COMMENT",
                            "comments": comments}, timeout=30)
    if r.status_code < 400:
        print(f"Posted {len(comments)} inline comment(s) on PR #{pr}.")
        return

    # GitHub rejects the entire review if any single comment falls outside the
    # diff. Losing every finding to one bad line number is worse than losing
    # the inline placement, so fall back to one summary comment carrying them all.
    print(f"Inline review rejected ({r.status_code}). Posting a summary instead.",
          file=sys.stderr)
    lines = [summary, "", "---", ""]
    for f in findings:
        lines.append(f"**`{f.get('path')}:{f.get('start_line')}`** — "
                     f"{str(f.get('severity', '')).upper()}\n\n"
                     f"{str(f.get('content', '')).strip()}\n")
    r2 = requests.post(f"{API}/repos/{repo}/issues/{pr}/comments", headers=headers,
                       json={"body": "\n".join(lines)}, timeout=30)
    r2.raise_for_status()
    print(f"Posted a summary comment with {len(findings)} finding(s).")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("review_json", type=Path)
    ap.add_argument("--pr", type=int, required=True)
    args = ap.parse_args(argv)

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not repo or not token:
        print("GITHUB_REPOSITORY and GITHUB_TOKEN are required", file=sys.stderr)
        return 2

    raw = args.review_json.read_text(encoding="utf-8").strip()
    if not raw:
        print("Review file is empty: the reviewer produced no output.",
              file=sys.stderr)
        return 1

    data = json.loads(raw)
    findings = dedupe(data.get("comments") or [])
    post(repo, args.pr, token, findings, summary_for(findings, data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
