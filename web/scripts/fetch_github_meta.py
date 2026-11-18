#!/usr/bin/env python3
"""
Fetch GitHub repository metadata (stars, last pushed date, custom OpenGraph image)
for all GitHub repositories referenced in catalog.json using GitHub GraphQL API.
Saves deterministic output to web/src/data/github_meta.json.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent.parent
CATALOG_JSON = WEB_DIR / "src" / "data" / "catalog.json"
OUTPUT_META_JSON = WEB_DIR / "src" / "data" / "github_meta.json"


def collect_repos() -> list[str]:
    catalog = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
    repos: set[str] = set()
    for sec in catalog.get("sections", []):
        for cat in sec.get("categories", []):
            for entry in cat.get("entries", []):
                repo = entry.get("githubRepo")
                if repo and "/" in repo:
                    repos.add(repo)
    return sorted(repos, key=str.lower)


def fetch_batch(batch: list[str]) -> dict[str, dict]:
    query_parts = ["query {"]
    alias_map: dict[str, str] = {}
    for idx, repo in enumerate(batch):
        owner, name = repo.split("/", 1)
        alias = f"r{idx}"
        alias_map[alias] = repo
        query_parts.append(
            f'  {alias}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{'
            " stargazerCount pushedAt openGraphImageUrl usesCustomOpenGraphImage isArchived }"
        )
    query_parts.append("}")
    query = "\n".join(query_parts)

    proc = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 and not proc.stdout:
        raise RuntimeError(f"gh api graphql failed: {proc.stderr}")

    payload = json.loads(proc.stdout)
    data = payload.get("data") or {}
    result: dict[str, dict] = {}
    for alias, repo in alias_map.items():
        node = data.get(alias)
        if not node:
            continue
        pushed_at = node.get("pushedAt")
        pushed_date = pushed_at[:10] if isinstance(pushed_at, str) and len(pushed_at) >= 10 else None
        custom_og = (
            node.get("openGraphImageUrl")
            if node.get("usesCustomOpenGraphImage")
            else None
        )
        result[repo] = {
            "stars": int(node.get("stargazerCount") or 0),
            "pushedAt": pushed_date,
            "customOgImage": custom_og,
            "isArchived": bool(node.get("isArchived")),
        }
    return result


def main() -> None:
    repos = collect_repos()
    print(f"Fetching GitHub metadata for {len(repos)} repositories...")

    existing: dict[str, dict] = {}
    if OUTPUT_META_JSON.exists():
        try:
            existing = json.loads(OUTPUT_META_JSON.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    meta = dict(existing)
    batch_size = 50
    for i in range(0, len(repos), batch_size):
        batch = repos[i : i + batch_size]
        batch_result = fetch_batch(batch)
        meta.update(batch_result)
        print(f"  Fetched {min(i + batch_size, len(repos))}/{len(repos)} ({len(batch_result)} resolved)")

    # Sort keys deterministically
    sorted_meta = {k: meta[k] for k in sorted(meta.keys(), key=str.lower) if k in repos}
    OUTPUT_META_JSON.write_text(
        json.dumps(sorted_meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"✅ Saved GitHub metadata for {len(sorted_meta)} repos to {OUTPUT_META_JSON}")


if __name__ == "__main__":
    main()
