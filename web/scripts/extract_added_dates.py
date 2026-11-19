#!/usr/bin/env python3
"""
Extract the first-added commit date (YYYY-MM-DD) for every catalog entry from
the git history of README.md, handling URL migrations (http->https,
blendermarket->superhivemarket, twitter->x) and title matching so refactored
links retain their original addition date.

Writes deterministic output to web/src/data/added_dates.json.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

WEB_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = WEB_DIR.parent
CATALOG_JSON = WEB_DIR / "src" / "data" / "catalog.json"
OUTPUT_ADDED_JSON = WEB_DIR / "src" / "data" / "added_dates.json"

MD_LINK_RE = re.compile(r"\[([^\[\]]+)\]\((https?://[^)\s]+)\)")
GENERIC_TITLES = {
    "repo",
    "github",
    "docs",
    "documentation",
    "free",
    "download",
    "link",
    "demo",
    "videodemo",
    "collections",
    "mixedlicense",
    "web",
    "website",
    "extension",
    "extensions",
    "blender",
}


def normalize_url(url: str) -> str:
    raw = url.strip()
    try:
        p = urlparse(raw)
        host = p.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        if host == "twitter.com":
            host = "x.com"
        elif host == "blendermarket.com":
            host = "superhivemarket.com"
        path = p.path.rstrip("/")
        query = f"?{p.query}" if p.query else ""
        return f"{host}{path}{query}".lower()
    except Exception:
        return raw.rstrip("/").lower()


def normalize_title(title: str) -> str:
    cleaned = re.sub(r"[`*_~]", "", title).strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "", cleaned)
    if len(slug) < 3 or slug in GENERIC_TITLES:
        return ""
    return slug


def scan_git_history() -> tuple[dict[str, str], dict[str, str]]:
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT_DIR),
            "log",
            "--reverse",
            "--format=COMMIT_DATE %cs",
            "-p",
            "--unified=0",
            "--",
            "README.md",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        check=True,
    )

    url_first: dict[str, str] = {}
    title_first: dict[str, str] = {}
    current_date = ""

    for line in proc.stdout.splitlines():
        if line.startswith("COMMIT_DATE "):
            current_date = line.split(" ", 1)[1].strip()
            continue
        if not current_date:
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        content = line[1:]
        for m in MD_LINK_RE.finditer(content):
            title_raw, url_raw = m.group(1), m.group(2)
            nu = normalize_url(url_raw)
            if nu and nu not in url_first:
                url_first[nu] = current_date
            nt = normalize_title(title_raw)
            if nt and nt not in title_first:
                title_first[nt] = current_date

    return url_first, title_first


def main() -> None:
    url_first, title_first = scan_git_history()
    catalog = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
    today = date.today().isoformat()

    added_dates: dict[str, str] = {}
    for sec in catalog.get("sections", []):
        for cat in sec.get("categories", []):
            for entry in cat.get("entries", []):
                if entry.get("kind") != "item" or not entry.get("url"):
                    continue
                url = entry["url"]
                nu = normalize_url(url)
                nt = normalize_title(entry["title"]["en"])
                candidates = [
                    d
                    for d in (url_first.get(nu), title_first.get(nt) if nt else None)
                    if d
                ]
                added_dates[url] = min(candidates) if candidates else today

    sorted_dates = {k: added_dates[k] for k in sorted(added_dates.keys(), key=str.lower)}
    OUTPUT_ADDED_JSON.write_text(
        json.dumps(sorted_dates, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    counts = Counter(sorted_dates.values())
    print(f"✅ Saved added dates for {len(sorted_dates)} items to {OUTPUT_ADDED_JSON}")
    print("   Latest 10 addition dates:")
    for dt, cnt in sorted(counts.items(), reverse=True)[:10]:
        print(f"     {dt}: {cnt} items")


if __name__ == "__main__":
    main()
