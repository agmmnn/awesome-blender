#!/usr/bin/env python3
"""
Lossless bilingual parser and catalog generator for Awesome Blender.

Reads `README.md` (English) and `README_ZH.md` (Chinese), validates line/URL parity,
and generates `web/src/data/catalog.json` as the single source of truth for the web app.

Usage:
    python3 web/scripts/build_catalog.py
    python3 web/scripts/build_catalog.py --check
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from collections import Counter
from datetime import date, datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any

WEB_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = WEB_DIR.parent
README_EN = ROOT_DIR / "README.md"
README_ZH = ROOT_DIR / "README_ZH.md"
OUTPUT_JSON = WEB_DIR / "src" / "data" / "catalog.json"
OUTPUT_LITE_JSON = WEB_DIR / "src" / "data" / "directory_lite.json"
OUTPUT_ADDED_DATES_JSON = WEB_DIR / "src" / "data" / "added_dates.json"
OUTPUT_PUBLIC_JSON = WEB_DIR / "public" / "catalog.json"
OUTPUT_SITEMAP = WEB_DIR / "public" / "sitemap.xml"
OUTPUT_FEED_XML = WEB_DIR / "public" / "feed.xml"
OUTPUT_LLMS_TXT = WEB_DIR / "public" / "llms.txt"
OUTPUT_LLMS_FULL_TXT = WEB_DIR / "public" / "llms-full.txt"
OUTPUT_LLMS_DIR = WEB_DIR / "public" / "llms"
OUTPUT_RECENT_MD = ROOT_DIR / "RECENT.md"
RECENT_MD_LIMIT = 100
README_RECENT_LIMIT = 5
FEED_LIMIT = 50
RECENT_START_MARKER = "<!-- RECENT:START -->"
RECENT_END_MARKER = "<!-- RECENT:END -->"

DIRECTORY_SECTION_IDS = {
    "add-ons",
    "ai-mcp",
    "resources",
    "standalone",
    "tutorials",
    "social",
}
EXCLUDED_DIRECTORY_CATEGORIES = {
    "resources/art-reference",
    "resources/related-awesome-lists",
}

MEDIA_SYMBOLS = {
    "▷": "video",
    "☰": "playlist",
    "☷": "channel",
    "🧾": "doc",
    "📦": "course",
}

LICENSE_CODES = ("gpl", "mit", "zero", "cc", "by", "nc")

URL_RE = re.compile(r"https?://[^\s\)\]>\"']+")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\)]+)\)")
HTML_BADGE_RE = re.compile(
    r'<a\s+href="(https?://[^"]+)"[^>]*>.*?<img\s+alt="([^"]+)"', re.I
)
GH_REPO_RE = re.compile(r"https?://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:[/?#]|$)")
EXT_ID_RE = re.compile(
    r"https?://extensions\.blender\.org/(?:add-ons|themes)/([A-Za-z0-9_.-]+?)(?:[/?#]|$)"
)


def slugify(text: str) -> str:
    """Create a URL-safe slug from an English heading or title."""
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    cleaned = re.sub(r"[^\w\s/-]", "", cleaned, flags=re.ASCII)
    cleaned = cleaned.strip().lower()
    cleaned = re.sub(r"[\s/_-]+", "-", cleaned).strip("-")
    return cleaned or "item"


def split_heading_emoji(raw: str) -> tuple[str | None, str, str | None]:
    """Extract optional leading emoji, clean title, and optional heading link."""
    text = raw.strip()
    heading_url: str | None = None
    m_link = re.match(r"^\[([^\]]+)\]\((https?://[^\)]+)\)$", text)
    if m_link:
        text = m_link.group(1).strip()
        heading_url = m_link.group(2).strip()

    # Match leading emoji/symbol characters (including ZWJ, skin tones, variation selectors, and spaces between them)
    # Stop at first ASCII letter/digit or CJK unified ideograph (\u4e00-\u9fff)
    m_emoji = re.match(r"^([^A-Za-z0-9\u4e00-\u9fff\[\(\"`]+)\s*(.*)$", text)
    if m_emoji and m_emoji.group(2).strip():
        emoji = re.sub(r"\s+", "", m_emoji.group(1))
        title = m_emoji.group(2).strip()
        return emoji, title, heading_url
    return None, text, heading_url


def strip_markdown_to_text(md: str) -> str:
    """Convert inline markdown to clean plain text for search and previews."""
    s = md
    # Remove linked and unlinked badge references like [![][repo]](url), [![market]](url), ![][gpl]
    s = re.sub(r"\[!\[\]\[\w+\]\]\([^\)]+\)", "", s)
    s = re.sub(r"\[!\[\w+\]\]\([^\)]+\)", "", s)
    s = re.sub(r"!\[\]\[\w+\]", "", s)
    # Replace double-bracket links [[docs]](url) with (docs)
    s = re.sub(r"\[\[([^\]]+)\]\]\([^\)]+\)", r"(\1)", s)
    # Replace normal markdown links [text](url) with text
    s = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", s)
    # Strip bold/italic/code markers
    s = re.sub(r"(\*\*|__|\*|_|\`)", "", s)
    s = s.replace(r"\_", "_")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_badges_and_clean(text: str) -> tuple[str, dict[str, Any]]:
    """
    Extract `💰` (or legacy `[$]`), `repo`, `market`, and license badges (`gpl`, `mit`, `zero`, `cc`, `by`, `nc`)
    from a markdown string, returning the cleaned markdown and badge metadata.
    """
    s = text
    is_paid = False
    if "💰" in s or "[$]" in s:
        is_paid = True
        s = re.sub(r"\s*(?:\[\$\]|💰)\s*", " ", s)

    repo_url: str | None = None
    for m in re.finditer(r"\[!\[\]\[repo\]\]\((https?://[^\)]+)\)", s):
        repo_url = m.group(1)
    s = re.sub(r"\s*\[!\[\]\[repo\]\]\([^\)]+\)", "", s)

    market_url: str | None = None
    for m in re.finditer(r"\[!(?:\[\])?\[market\]\]\((https?://[^\)]+)\)", s):
        market_url = m.group(1)
    s = re.sub(r"\s*\[!(?:\[\])?\[market\]\]\([^\)]+\)", "", s)

    licenses: list[str] = []
    license_urls: dict[str, str] = {}
    for code in LICENSE_CODES:
        linked_pat = re.compile(rf"\[!\[\]\[{code}\]\]\((https?://[^\)]+)\)")
        for m in linked_pat.finditer(s):
            if code not in licenses:
                licenses.append(code)
            license_urls[code] = m.group(1)
        s = linked_pat.sub("", s)

        bare_pat = re.compile(rf"!\[\]\[{code}\]")
        if bare_pat.search(s):
            if code not in licenses:
                licenses.append(code)
        s = bare_pat.sub("", s)

    # Also detect Leading/Trailing media symbols
    media_type: str | None = None
    for sym, mtype in MEDIA_SYMBOLS.items():
        if sym in s:
            media_type = mtype
            s = s.replace(sym, "")
            break
    s = s.replace("🪑", "").strip()

    return s.strip(), {
        "isPaid": is_paid,
        "repoUrl": repo_url,
        "marketUrl": market_url,
        "licenses": licenses,
        "licenseUrls": license_urls,
        "mediaType": media_type,
    }


def split_colon_outside_brackets(s: str, is_zh: bool = False) -> tuple[str, str] | None:
    """
    Split a bullet line into (lhs, rhs) on the first ` : ` (or `: ` / `：`)
    that occurs OUTSIDE `[...]` and `(...)`.
    """
    depth_sq = 0
    depth_par = 0
    n = len(s)
    for i, ch in enumerate(s):
        if ch == "[":
            depth_sq += 1
        elif ch == "]" and depth_sq > 0:
            depth_sq -= 1
        elif ch == "(":
            depth_par += 1
        elif ch == ")" and depth_par > 0:
            depth_par -= 1
        elif depth_sq == 0 and depth_par == 0:
            if is_zh and ch == "：":
                return s[:i].strip(), s[i + 1 :].strip()
            if s[i : i + 3] == " : ":
                return s[:i].strip(), s[i + 3 :].strip()
            if s[i : i + 2] == ": " and i > 0:
                return s[:i].strip(), s[i + 2 :].strip()
    return None


def classify_platforms(urls: list[str], is_open_source_hint: bool) -> tuple[list[str], str | None, str | None]:
    """Derive platform tags, primary GitHub `owner/repo`, and Blender Extension ID from entry URLs."""
    platforms: list[str] = []
    gh_repo: str | None = None
    ext_id: str | None = None

    for u in urls:
        ul = u.lower()
        if "extensions.blender.org" in ul or "projects.blender.org/extensions" in ul:
            if "extensions" not in platforms:
                platforms.append("extensions")
            m_ext = EXT_ID_RE.search(u)
            if m_ext and not ext_id:
                ext_id = m_ext.group(1)
        if "github.com/" in ul:
            if "github" not in platforms:
                platforms.append("github")
            m_gh = GH_REPO_RE.search(u)
            if m_gh and not gh_repo:
                candidate = m_gh.group(1)
                if candidate.endswith(".git"):
                    candidate = candidate[:-4]
                gh_repo = candidate
        if "gitlab.com/" in ul and "gitlab" not in platforms:
            platforms.append("gitlab")
        if "bitbucket.org/" in ul and "bitbucket" not in platforms:
            platforms.append("bitbucket")
        if "superhivemarket.com/" in ul and "superhive" not in platforms:
            platforms.append("superhive")
        if "gumroad.com/" in ul and "gumroad" not in platforms:
            platforms.append("gumroad")
        if ("youtube.com/" in ul or "youtu.be/" in ul) and "youtube" not in platforms:
            platforms.append("youtube")
        if "docs.blender.org/" in ul and "blender-docs" not in platforms:
            platforms.append("blender-docs")

    if (
        is_open_source_hint
        or "github" in platforms
        or "gitlab" in platforms
        or "bitbucket" in platforms
    ):
        if "open-source" not in platforms:
            platforms.append("open-source")

    return platforms, gh_repo, ext_id


def parse_bullet_pair(
    line_no: int,
    en_body: str,
    zh_body: str,
    section_id: str,
    category_id: str,
    subgroup_id: str | None,
    subgroup_title: dict[str, str] | None,
) -> dict[str, Any]:
    """Parse a matched EN/ZH content bullet into a structured CatalogEntry."""
    all_en_urls = URL_RE.findall(en_body)
    en_clean, b_en = extract_badges_and_clean(en_body)
    zh_clean, _ = extract_badges_and_clean(zh_body)

    en_split = split_colon_outside_brackets(en_clean, is_zh=False)
    zh_split = split_colon_outside_brackets(zh_clean, is_zh=True) or split_colon_outside_brackets(
        zh_clean, is_zh=False
    )

    kind = "item"
    title_en = ""
    title_zh = ""
    primary_url: str | None = None
    desc_md_en = ""
    desc_md_zh = ""
    secondary_links: list[dict[str, Any]] = []

    if en_split:
        lhs_en, rhs_en = en_split
        lhs_zh, rhs_zh = zh_split if zh_split else (zh_clean, "")

        lhs_links_en = MD_LINK_RE.findall(lhs_en)
        lhs_links_zh = MD_LINK_RE.findall(lhs_zh)

        if not lhs_links_en:
            # e.g. `Format Importers : [Daz Importer](...), [glTF-Blender-IO](...)`
            kind = "collection"
            title_en = strip_markdown_to_text(lhs_en).rstrip(":")
            title_zh = strip_markdown_to_text(lhs_zh).rstrip("：:")
            rhs_links_en = MD_LINK_RE.findall(rhs_en)
            rhs_links_zh = MD_LINK_RE.findall(rhs_zh)
            for idx, (lbl_e, u_e) in enumerate(rhs_links_en):
                lbl_z = rhs_links_zh[idx][0] if idx < len(rhs_links_zh) else lbl_e
                secondary_links.append(
                    {
                        "label": {"en": strip_markdown_to_text(lbl_e), "zh": strip_markdown_to_text(lbl_z)},
                        "url": u_e,
                        "type": "collection-item",
                    }
                )
            desc_md_en = rhs_en
            desc_md_zh = rhs_zh
        else:
            # Starts with 1 or 2 links on LHS
            title_en = strip_markdown_to_text(lhs_links_en[0][0])
            title_zh = (
                strip_markdown_to_text(lhs_links_zh[0][0])
                if lhs_links_zh
                else title_en
            )
            primary_url = lhs_links_en[0][1]

            # If dual link on LHS, e.g. `[Export EDL](...) & [Import EDL](...)`
            for extra_idx in range(1, len(lhs_links_en)):
                lbl_e, u_e = lhs_links_en[extra_idx]
                lbl_z = (
                    lhs_links_zh[extra_idx][0]
                    if extra_idx < len(lhs_links_zh)
                    else lbl_e
                )
                secondary_links.append(
                    {
                        "label": {"en": strip_markdown_to_text(lbl_e), "zh": strip_markdown_to_text(lbl_z)},
                        "url": u_e,
                        "type": "companion",
                    }
                )

            desc_md_en = rhs_en
            desc_md_zh = rhs_zh

            # Extract any inline links inside RHS description
            rhs_links_en = MD_LINK_RE.findall(rhs_en)
            rhs_links_zh = MD_LINK_RE.findall(rhs_zh)
            for idx, (lbl_e, u_e) in enumerate(rhs_links_en):
                lbl_z = rhs_links_zh[idx][0] if idx < len(rhs_links_zh) else lbl_e
                clean_lbl_e = lbl_e.strip("[]")
                clean_lbl_z = lbl_z.strip("[]")
                ltype = "other"
                low = clean_lbl_e.lower()
                if low in ("docs", "doc", "manual", "documentation", "wiki"):
                    ltype = "docs"
                elif low in ("website", "site", "homepage"):
                    ltype = "website"
                elif low in ("thread", "post", "forum", "blenderartists"):
                    ltype = "thread"
                elif low in ("video", "youtube", "demo", "more info", "info"):
                    ltype = "info"
                secondary_links.append(
                    {
                        "label": {"en": clean_lbl_e, "zh": clean_lbl_z},
                        "url": u_e,
                        "type": ltype,
                    }
                )
    else:
        # No ` : ` separator outside brackets
        links_en = MD_LINK_RE.findall(en_clean)
        links_zh = MD_LINK_RE.findall(zh_clean)

        if len(links_en) == 1:
            lbl_e, u_e = links_en[0]
            lbl_z = links_zh[0][0] if links_zh else lbl_e
            title_en = strip_markdown_to_text(lbl_e).rstrip(".")
            title_zh = strip_markdown_to_text(lbl_z).rstrip("。.")
            primary_url = u_e
            # Check if there is text outside the link (like L113 intro bullet)
            leftover_en = MD_LINK_RE.sub("", en_clean).strip(" .")
            leftover_zh = MD_LINK_RE.sub("", zh_clean).strip(" 。.")
            if leftover_en:
                desc_md_en = en_clean
                desc_md_zh = zh_clean
        elif len(links_en) >= 2:
            # Check if it's a dual tutorial/doc item with `&` or `|` vs a multi-link collection
            non_link_text = MD_LINK_RE.sub("", en_clean).strip()
            if (
                len(links_en) == 2
                and ("&" in non_link_text or "[[part2]]" in en_clean.lower())
            ):
                title_en = strip_markdown_to_text(links_en[0][0]).rstrip(".")
                title_zh = (
                    strip_markdown_to_text(links_zh[0][0]).rstrip("。.")
                    if links_zh
                    else title_en
                )
                primary_url = links_en[0][1]
                lbl2_e, u2_e = links_en[1]
                lbl2_z = links_zh[1][0] if len(links_zh) > 1 else lbl2_e
                secondary_links.append(
                    {
                        "label": {
                            "en": strip_markdown_to_text(lbl2_e).strip("[]"),
                            "zh": strip_markdown_to_text(lbl2_z).strip("[]"),
                        },
                        "url": u2_e,
                        "type": "companion",
                    }
                )
            else:
                kind = "collection"
                joined_en = " / ".join(strip_markdown_to_text(lbl) for lbl, _ in links_en[:3])
                if len(links_en) > 3:
                    joined_en = (
                        subgroup_title["en"]
                        if subgroup_title
                        else f"{joined_en} (+{len(links_en) - 3} more)"
                    )
                joined_zh = " / ".join(strip_markdown_to_text(lbl) for lbl, _ in links_zh[:3])
                if len(links_zh) > 3:
                    joined_zh = (
                        subgroup_title["zh"]
                        if subgroup_title
                        else f"{joined_zh} (等 {len(links_zh)} 项)"
                    )
                title_en = subgroup_title["en"] if (subgroup_title and len(links_en) > 3) else joined_en
                title_zh = subgroup_title["zh"] if (subgroup_title and len(links_zh) > 3) else joined_zh
                for idx, (lbl_e, u_e) in enumerate(links_en):
                    lbl_z = links_zh[idx][0] if idx < len(links_zh) else lbl_e
                    secondary_links.append(
                        {
                            "label": {
                                "en": strip_markdown_to_text(lbl_e),
                                "zh": strip_markdown_to_text(lbl_z),
                            },
                            "url": u_e,
                            "type": "collection-item",
                        }
                    )
                desc_md_en = en_clean
                desc_md_zh = zh_clean

    # Add repo, market, and license URLs into secondary_links if present
    if b_en["repoUrl"]:
        secondary_links.append(
            {
                "label": {"en": "Repository", "zh": "源码仓库"},
                "url": b_en["repoUrl"],
                "type": "repo",
            }
        )
    if b_en["marketUrl"]:
        secondary_links.append(
            {
                "label": {"en": "Superhive", "zh": "Superhive"},
                "url": b_en["marketUrl"],
                "type": "market",
            }
        )
    for code, lurl in b_en["licenseUrls"].items():
        secondary_links.append(
            {
                "label": {"en": f"License ({code.upper()})", "zh": f"许可证 ({code.upper()})"},
                "url": lurl,
                "type": "license",
            }
        )

    is_open_source_hint = bool(
        b_en["repoUrl"]
        or any(c in ("gpl", "mit") for c in b_en["licenses"])
    )
    platforms, gh_repo, ext_id = classify_platforms(all_en_urls, is_open_source_hint)

    slug = slugify(title_en)[:48]
    entry_id = f"L{line_no}-{slug}"

    return {
        "id": entry_id,
        "line": line_no,
        "kind": kind,
        "sectionId": section_id,
        "categoryId": category_id,
        "subgroupId": subgroup_id,
        "subgroup": subgroup_title,
        "title": {"en": title_en, "zh": title_zh},
        "url": primary_url,
        "description": {
            "en": strip_markdown_to_text(desc_md_en),
            "zh": strip_markdown_to_text(desc_md_zh),
        },
        "descriptionMd": {"en": desc_md_en, "zh": desc_md_zh},
        "secondaryLinks": secondary_links,
        "allUrls": all_en_urls,
        "isPaid": b_en["isPaid"],
        "isFree": not b_en["isPaid"],
        "licenses": b_en["licenses"],
        "mediaType": b_en["mediaType"],
        "platforms": platforms,
        "githubRepo": gh_repo,
        "blenderExtensionId": ext_id,
    }


def build_catalog() -> tuple[dict[str, Any], list[str]]:
    """Parse README.md and README_ZH.md into the unified catalog dict and return any warnings."""
    en_lines = README_EN.read_text(encoding="utf-8").splitlines()
    zh_lines = README_ZH.read_text(encoding="utf-8").splitlines()

    errors: list[str] = []
    if len(en_lines) != len(zh_lines):
        errors.append(
            f"Line count mismatch: README.md has {len(en_lines)} lines, README_ZH.md has {len(zh_lines)} lines"
        )

    sections: list[dict[str, Any]] = []
    cur_section: dict[str, Any] | None = None
    cur_category: dict[str, Any] | None = None
    cur_subgroup: dict[str, Any] | None = None
    last_top_entry: dict[str, Any] | None = None

    in_comment = False
    in_badge_p = False
    badge_p_lines_en: list[tuple[int, str]] = []
    badge_p_lines_zh: list[tuple[int, str]] = []

    parsed_urls: list[str] = []
    expected_urls: list[str] = []

    # Content starts at first H2 (`## 🔮 Add-ons`) and stops before `### Symbols`
    content_started = False

    for idx in range(min(len(en_lines), len(zh_lines))):
        line_no = idx + 1
        raw_en = en_lines[idx].rstrip()
        raw_zh = zh_lines[idx].rstrip()

        # Track multi-line HTML comments
        if "<!--" in raw_en:
            if "-->" not in raw_en:
                in_comment = True
            continue
        if in_comment:
            if "-->" in raw_en:
                in_comment = False
            continue

        if raw_en.startswith("## "):
            content_started = True

        if not content_started:
            continue

        if raw_en.startswith("### Symbols"):
            break

        # Ignore horizontal rules and Back to top links
        if not raw_en or raw_en == "---" or 'href="#table"' in raw_en:
            continue

        # Record all URLs on active content lines for lossless audit
        line_en_urls = URL_RE.findall(raw_en)
        line_zh_urls = URL_RE.findall(raw_zh)
        if line_en_urls != line_zh_urls:
            errors.append(
                f"L{line_no} URL parity mismatch: EN={line_en_urls} vs ZH={line_zh_urls}"
            )
        expected_urls.extend(line_en_urls)

        # 1. H2 Section
        if raw_en.startswith("## "):
            emoji, title_en, _ = split_heading_emoji(raw_en[3:])
            _, title_zh, _ = split_heading_emoji(raw_zh[3:])
            sec_id = slugify(title_en)
            cur_section = {
                "id": sec_id,
                "line": line_no,
                "emoji": emoji,
                "title": {"en": title_en, "zh": title_zh},
                "banners": [],
                "categories": [],
            }
            sections.append(cur_section)
            cur_category = None
            cur_subgroup = None
            last_top_entry = None
            continue

        # 2. H3 Category
        if raw_en.startswith("### "):
            assert cur_section is not None, f"H3 before H2 at L{line_no}"
            emoji, title_en, h_url = split_heading_emoji(raw_en[4:])
            _, title_zh, _ = split_heading_emoji(raw_zh[4:])
            cat_slug = slugify(title_en)
            cat_id = f"{cur_section['id']}/{cat_slug}"
            cur_category = {
                "id": cat_id,
                "slug": cat_slug,
                "sectionId": cur_section["id"],
                "line": line_no,
                "emoji": emoji,
                "title": {"en": title_en, "zh": title_zh},
                "url": h_url,
                "note": None,
                "subgroups": [],
                "entries": [],
            }
            if h_url:
                parsed_urls.append(h_url)
            cur_section["categories"].append(cur_category)
            cur_subgroup = None
            last_top_entry = None
            continue

        # 3. Multi-line <p> badge blocks (Explore Blender & Explore Artworks)
        if raw_en == "<p>":
            in_badge_p = True
            badge_p_lines_en = []
            badge_p_lines_zh = []
            continue
        if in_badge_p:
            if raw_en == "</p>":
                in_badge_p = False
                for (b_line, b_en), (_, b_zh) in zip(badge_p_lines_en, badge_p_lines_zh):
                    m_b = HTML_BADGE_RE.search(b_en)
                    b_urls = URL_RE.findall(b_en)
                    parsed_urls.extend(b_urls)
                    if m_b:
                        href, alt = m_b.group(1), m_b.group(2)
                        if cur_category is not None:
                            cur_category["entries"].append(
                                {
                                    "id": f"L{b_line}-{slugify(alt)}",
                                    "line": b_line,
                                    "kind": "quick-link",
                                    "sectionId": cur_section["id"],
                                    "categoryId": cur_category["id"],
                                    "subgroupId": None,
                                    "subgroup": None,
                                    "title": {"en": alt, "zh": alt},
                                    "url": href,
                                    "description": {"en": "", "zh": ""},
                                    "descriptionMd": {"en": "", "zh": ""},
                                    "secondaryLinks": [],
                                    "allUrls": b_urls,
                                    "isPaid": False,
                                    "isFree": True,
                                    "licenses": [],
                                    "mediaType": None,
                                    "platforms": [],
                                    "githubRepo": None,
                                    "blenderExtensionId": None,
                                }
                            )
                        elif cur_section is not None:
                            cur_section["banners"].append(
                                {
                                    "line": b_line,
                                    "title": {"en": alt, "zh": alt},
                                    "url": href,
                                    "allUrls": b_urls,
                                }
                            )
                continue
            else:
                badge_p_lines_en.append((line_no, raw_en))
                badge_p_lines_zh.append((line_no, raw_zh))
                continue

        # 4. Blockquote note (e.g. `> _`▷` video..._`)
        if raw_en.startswith("> "):
            if cur_category is not None:
                cur_category["note"] = {
                    "en": strip_markdown_to_text(raw_en[2:]),
                    "zh": strip_markdown_to_text(raw_zh[2:]),
                }
            elif cur_section is not None:
                cur_section["banners"].append(
                    {
                        "line": line_no,
                        "title": {
                            "en": strip_markdown_to_text(raw_en[2:]),
                            "zh": strip_markdown_to_text(raw_zh[2:]),
                        },
                        "url": None,
                        "allUrls": line_en_urls,
                    }
                )
            parsed_urls.extend(line_en_urls)
            continue

        # 5. Section intro bullet before first H3 (e.g. L113 under `## 🔮 Add-ons`)
        if cur_category is None and raw_en.startswith("- "):
            assert cur_section is not None
            cur_section["banners"].append(
                {
                    "line": line_no,
                    "title": {
                        "en": strip_markdown_to_text(raw_en[2:]),
                        "zh": strip_markdown_to_text(raw_zh[2:]),
                    },
                    "url": line_en_urls[0] if line_en_urls else None,
                    "allUrls": line_en_urls,
                }
            )
            parsed_urls.extend(line_en_urls)
            continue

        assert cur_category is not None, f"Content outside H3 at L{line_no}: {raw_en}"

        # 6. Top-level bullet (`- ...`)
        if raw_en.startswith("- "):
            body_en = raw_en[2:].strip()
            body_zh = raw_zh[2:].strip()

            # Check if this top-level bullet is a subgroup header:
            # Either ends with `:` and has no links, OR is `[gumroad/blender](...):` / `[udemy/blender](...):`
            is_plain_subgroup = body_en.endswith(":") and "](" not in body_en
            is_linked_subgroup = bool(
                re.match(r"^\[[^\]]+\]\(https?://[^\)]+\):$", body_en)
            )
            if is_plain_subgroup or is_linked_subgroup:
                sg_clean_en, sg_badges = extract_badges_and_clean(body_en.rstrip(":"))
                sg_clean_zh, _ = extract_badges_and_clean(body_zh.rstrip("：:"))
                sg_links = MD_LINK_RE.findall(sg_clean_en)
                sg_url = sg_links[0][1] if sg_links else None
                sg_title_en = strip_markdown_to_text(sg_clean_en)
                sg_title_zh = strip_markdown_to_text(sg_clean_zh)
                sg_id = slugify(sg_title_en)
                cur_subgroup = {
                    "id": sg_id,
                    "line": line_no,
                    "title": {"en": sg_title_en, "zh": sg_title_zh},
                    "url": sg_url,
                    "mediaType": sg_badges["mediaType"],
                }
                cur_category["subgroups"].append(cur_subgroup)
                if sg_url:
                    parsed_urls.append(sg_url)
                last_top_entry = None
                continue

            # Otherwise it's a top-level content bullet (reset active subgroup)
            cur_subgroup = None
            entry = parse_bullet_pair(
                line_no=line_no,
                en_body=body_en,
                zh_body=body_zh,
                section_id=cur_section["id"],
                category_id=cur_category["id"],
                subgroup_id=None,
                subgroup_title=None,
            )
            cur_category["entries"].append(entry)
            last_top_entry = entry
            parsed_urls.extend(entry["allUrls"])
            continue

        # 7. Indented bullet (`    - ...`)
        if raw_en.startswith("    - "):
            body_en = raw_en[6:].strip()
            body_zh = raw_zh[6:].strip()
            if cur_subgroup is not None:
                entry = parse_bullet_pair(
                    line_no=line_no,
                    en_body=body_en,
                    zh_body=body_zh,
                    section_id=cur_section["id"],
                    category_id=cur_category["id"],
                    subgroup_id=cur_subgroup["id"],
                    subgroup_title=cur_subgroup["title"],
                )
                cur_category["entries"].append(entry)
                parsed_urls.extend(entry["allUrls"])
            elif last_top_entry is not None:
                # Child of a non-subgroup top-level item (e.g. Radeon ProRender -> USD Hydra, or Nodevember -> See works)
                child = parse_bullet_pair(
                    line_no=line_no,
                    en_body=body_en,
                    zh_body=body_zh,
                    section_id=cur_section["id"],
                    category_id=cur_category["id"],
                    subgroup_id=None,
                    subgroup_title=None,
                )
                child["parentId"] = last_top_entry["id"]
                cur_category["entries"].append(child)
                parsed_urls.extend(child["allUrls"])
            else:
                errors.append(f"Orphan indented bullet at L{line_no}: {raw_en}")
            continue

        # 8. Pipe-separated quick links (e.g. L798 Documentation, L802 Development)
        if " | " in raw_en and "](" in raw_en:
            links_en = MD_LINK_RE.findall(raw_en)
            links_zh = MD_LINK_RE.findall(raw_zh)
            for l_idx, (lbl_e, u_e) in enumerate(links_en):
                lbl_z = links_zh[l_idx][0] if l_idx < len(links_zh) else lbl_e
                cur_category["entries"].append(
                    {
                        "id": f"L{line_no}-{l_idx + 1}-{slugify(lbl_e)}",
                        "line": line_no,
                        "kind": "quick-link",
                        "sectionId": cur_section["id"],
                        "categoryId": cur_category["id"],
                        "subgroupId": None,
                        "subgroup": None,
                        "title": {
                            "en": strip_markdown_to_text(lbl_e),
                            "zh": strip_markdown_to_text(lbl_z),
                        },
                        "url": u_e,
                        "description": {"en": "", "zh": ""},
                        "descriptionMd": {"en": "", "zh": ""},
                        "secondaryLinks": [],
                        "allUrls": [u_e],
                        "isPaid": False,
                        "isFree": True,
                        "licenses": [],
                        "mediaType": None,
                        "platforms": ["blender-docs"],
                        "githubRepo": None,
                        "blenderExtensionId": None,
                    }
                )
                parsed_urls.append(u_e)
            continue

        # 9. Italic category note (e.g. `_Some accounts where you can find..._`)
        if raw_en.startswith("_") and raw_en.endswith("_") and "](" not in raw_en:
            cur_category["note"] = {
                "en": strip_markdown_to_text(raw_en),
                "zh": strip_markdown_to_text(raw_zh),
            }
            continue

        # 10. Social handle line (`[@handle](https://x.com/handle),`)
        m_handle = MD_LINK_RE.search(raw_en)
        if m_handle and raw_en.lstrip().startswith("[@"):
            lbl_e, u_e = m_handle.group(1), m_handle.group(2)
            clean_handle = lbl_e.replace(r"\_", "_")
            cur_category["entries"].append(
                {
                    "id": f"L{line_no}-{slugify(clean_handle)}",
                    "line": line_no,
                    "kind": "social-handle",
                    "sectionId": cur_section["id"],
                    "categoryId": cur_category["id"],
                    "subgroupId": None,
                    "subgroup": None,
                    "title": {"en": clean_handle, "zh": clean_handle},
                    "url": u_e,
                    "description": {"en": "", "zh": ""},
                    "descriptionMd": {"en": "", "zh": ""},
                    "secondaryLinks": [],
                    "allUrls": [u_e],
                    "isPaid": False,
                    "isFree": True,
                    "licenses": [],
                    "mediaType": None,
                    "platforms": [],
                    "githubRepo": None,
                    "blenderExtensionId": None,
                }
            )
            parsed_urls.append(u_e)
            continue

        errors.append(f"Unrecognized line at L{line_no}: {raw_en}")

    # Verify lossless URL capture
    c_expected = Counter(expected_urls)
    c_parsed = Counter(parsed_urls)
    missing_urls = list((c_expected - c_parsed).elements())
    extra_urls = list((c_parsed - c_expected).elements())
    if missing_urls:
        errors.append(f"Missing {len(missing_urls)} URLs from catalog: {missing_urls[:10]}")
    if extra_urls:
        errors.append(f"Extra {len(extra_urls)} URLs in catalog: {extra_urls[:10]}")

    # Compute aggregate stats
    all_entries = [
        e for sec in sections for cat in sec["categories"] for e in cat["entries"]
    ]
    all_subgroups = [
        sg for sec in sections for cat in sec["categories"] for sg in cat["subgroups"]
    ]
    lic_counter: Counter[str] = Counter()
    plat_counter: Counter[str] = Counter()
    unique_gh: set[str] = set()
    unique_ext: set[str] = set()

    for e in all_entries:
        for lic in e["licenses"]:
            lic_counter[lic] += 1
        for p in e["platforms"]:
            plat_counter[p] += 1
        if e["githubRepo"]:
            unique_gh.add(e["githubRepo"].lower())
        if e["blenderExtensionId"]:
            unique_ext.add(e["blenderExtensionId"].lower())

    stats = {
        "totalSections": len(sections),
        "totalCategories": sum(len(s["categories"]) for s in sections),
        "totalSubgroups": len(all_subgroups),
        "totalEntries": len(all_entries),
        "entryKinds": dict(Counter(e["kind"] for e in all_entries)),
        "totalContentUrls": len(parsed_urls),
        "uniqueContentUrls": len(set(parsed_urls)),
        "paidEntries": sum(1 for e in all_entries if e["isPaid"]),
        "freeEntries": sum(1 for e in all_entries if e["isFree"]),
        "uniqueGithubRepos": len(unique_gh),
        "uniqueBlenderExtensions": len(unique_ext),
        "licenseCounts": dict(lic_counter),
        "platformCounts": dict(plat_counter),
    }

    catalog = {
        "version": "1.0.0",
        "stats": stats,
        "sections": sections,
    }
    return catalog, errors


def build_sitemap_xml(catalog: dict[str, Any], site_url: str) -> str:
    """Generate a bilingual sitemap.xml for indexable directory views."""
    base = site_url.rstrip("/")

    def add_lang_param(url: str, lang: str) -> str:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}lang={lang}"

    entries: list[tuple[str, str, str]] = [(f"{base}/", "weekly", "1.0")]

    for sec in catalog["sections"]:
        if sec["id"] not in DIRECTORY_SECTION_IDS:
            continue
        sec_url = f"{base}/?section={sec['id']}"
        entries.append((sec_url, "weekly", "0.9"))

        for cat in sec["categories"]:
            if cat["id"] in EXCLUDED_DIRECTORY_CATEGORIES:
                continue
            valid_items = [
                e for e in cat["entries"] if e["kind"] == "item" and e.get("url")
            ]
            if not valid_items:
                continue
            cat_url = f"{base}/?section={sec['id']}&category={cat['slug']}"
            entries.append((cat_url, "weekly", "0.8"))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for url, changefreq, priority in entries:
        zh_url = add_lang_param(url, "zh")
        esc_en = html.escape(url, quote=True)
        esc_zh = html.escape(zh_url, quote=True)
        lines.extend(
            [
                "  <url>",
                f"    <loc>{esc_en}</loc>",
                f'    <xhtml:link rel="alternate" hreflang="en" href="{esc_en}" />',
                f'    <xhtml:link rel="alternate" hreflang="zh" href="{esc_zh}" />',
                f'    <xhtml:link rel="alternate" hreflang="x-default" href="{esc_en}" />',
                f"    <changefreq>{changefreq}</changefreq>",
                f"    <priority>{priority}</priority>",
                "  </url>",
            ]
        )
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def _format_llms_entry(entry: dict[str, Any]) -> str:
    """Format a non-social CatalogEntry as a concise Markdown bullet for LLMs."""
    indent = "  " if entry.get("parentId") else ""
    kind = entry.get("kind", "item")
    title = entry["title"]["en"]
    url = entry.get("url")
    desc = (
        entry.get("descriptionMd", {}).get("en")
        or entry.get("description", {}).get("en")
        or ""
    ).strip()

    tags: list[str] = []
    if entry.get("isPaid"):
        tags.append("paid")
    if entry.get("mediaType"):
        tags.append(entry["mediaType"])
    for lic in entry.get("licenses", []):
        tags.append(lic.upper())
    if entry.get("blenderExtensionId"):
        tags.append(f"ext:{entry['blenderExtensionId']}")
    elif "open-source" in entry.get("platforms", []) and not any(
        l in ("gpl", "mit", "zero") for l in entry.get("licenses", [])
    ):
        tags.append("open-source")

    if kind == "collection":
        links = [
            f"[{sl['label']['en']}]({sl['url']})"
            for sl in entry.get("secondaryLinks", [])
            if sl.get("url")
        ]
        if links:
            return f"{indent}- **{title}**: {', '.join(links)}"
        return f"{indent}- **{title}**"

    head = f"[{title}]({url})" if url else f"**{title}**"

    extra_links: list[str] = []
    for sl in entry.get("secondaryLinks", []):
        s_url = sl.get("url")
        if not s_url or s_url == url or sl.get("type") == "license":
            continue
        s_lbl = sl.get("label", {}).get("en") or sl.get("type") or "Link"
        extra_links.append(f"[{s_lbl}]({s_url})")

    parts = [head]
    if desc:
        parts.append(f": {desc}")
    if tags:
        parts.append(f" `[{' · '.join(tags)}]`")
    if extra_links:
        parts.append(f" ({', '.join(extra_links)})")
    return f"{indent}- {''.join(parts)}"


def build_llms_section_md(
    sec: dict[str, Any], site_url: str, heading_level: int = 1
) -> str:
    """Render one top-level catalog section into clean LLM-friendly Markdown."""
    base = site_url.rstrip("/")
    h_sec = "#" * heading_level
    h_cat = "#" * (heading_level + 1)
    h_sub = "#" * (heading_level + 2)

    total_entries = sum(len(cat["entries"]) for cat in sec["categories"])
    lines: list[str] = [f"{h_sec} {sec['title']['en']}"]
    if heading_level == 1:
        lines.append("")
        lines.append(
            f"> {total_entries} curated entries across {len(sec['categories'])} categories. Index: {base}/llms.txt"
        )

    if sec.get("banners"):
        lines.append("")
    for banner in sec.get("banners", []):
        b_title = banner.get("title", {}).get("en", "")
        b_url = banner.get("url")
        if b_url and b_title:
            lines.append(f"- [{b_title}]({b_url})")
        elif b_title:
            lines.append(f"- {b_title}")

    for cat in sec["categories"]:
        lines.append("")
        cat_heading = (
            f"[{cat['title']['en']}]({cat['url']})" if cat.get("url") else cat["title"]["en"]
        )
        lines.append(f"{h_cat} {cat_heading}")
        if cat.get("note") and cat["note"].get("en"):
            lines.append("")
            lines.append(f"> {cat['note']['en']}")

        sg_map = {sg["id"]: sg for sg in cat.get("subgroups", [])}
        current_sg: str | None = "__unset__"
        social_handles: list[str] = []

        def flush_handles() -> None:
            if social_handles:
                lines.append("")
                lines.append(f"- Accounts: {', '.join(social_handles)}")
                social_handles.clear()

        for entry in cat["entries"]:
            if entry.get("kind") == "social-handle":
                social_handles.append(f"[{entry['title']['en']}]({entry['url']})")
                continue

            flush_handles()
            sg_id = entry.get("subgroupId")
            if sg_id != current_sg:
                current_sg = sg_id
                if sg_id and sg_id in sg_map:
                    sg = sg_map[sg_id]
                    sg_label = (
                        f"[{sg['title']['en']}]({sg['url']})"
                        if sg.get("url")
                        else sg["title"]["en"]
                    )
                    lines.append("")
                    lines.append(f"{h_sub} {sg_label}")
                lines.append("")

            if current_sg == "__unset__":
                current_sg = None
                lines.append("")

            lines.append(_format_llms_entry(entry))

        flush_handles()

    return "\n".join(lines).rstrip() + "\n"


def build_llms_txt(catalog: dict[str, Any], site_url: str) -> str:
    """Generate the `llmstxt.org`-compliant root index file."""
    base = site_url.rstrip("/")
    st = catalog["stats"]
    lines: list[str] = [
        "# Awesome Blender",
        "",
        (
            f"> Curated bilingual (EN/ZH) directory of {st['totalEntries']} Blender add-ons, "
            f"AI & MCP tools, 3D assets, HDRIs, standalone utilities, tutorials, and community resources — "
            f"{st['freeEntries']} free entries, {st['uniqueGithubRepos']} GitHub repositories, "
            f"and {st['uniqueBlenderExtensions']} official Blender Extensions."
        ),
        "",
        (
            "Use the section Markdown indexes or JSON catalog below to retrieve verified URLs, "
            "licenses, and descriptions without hallucinating links. The web directory at "
            f"`{base}/` supports query filters: `?section=`, `?category=`, `?subgroup=`, `?q=`, "
            "`?price=free|paid`, `?platform=extensions|github|open-source|superhive|gumroad`, and "
            "`?license=gpl|mit|zero|cc`."
        ),
        "",
        "## Machine-Readable Catalog",
        "",
        (
            f"- [Full Catalog (Markdown)]({base}/llms-full.txt): Complete plain-Markdown dump of all "
            f"{st['totalSections']} sections, {st['totalCategories']} categories, and {st['totalEntries']} entries."
        ),
        (
            f"- [Structured Catalog (JSON)]({base}/catalog.json): Lossless bilingual EN/ZH catalog JSON "
            "(aggregate `stats` plus structured `sections -> categories -> entries`)."
        ),
        (
            f"- [Interactive Web Directory]({base}/): Searchable directory of downloadable add-ons, "
            "AI/MCP tools, 3D assets, and standalone apps."
        ),
        "",
        "## Sections",
        "",
    ]

    for sec in catalog["sections"]:
        cnt = sum(len(cat["entries"]) for cat in sec["categories"])
        preview_cats = ", ".join(cat["title"]["en"] for cat in sec["categories"][:5])
        if len(sec["categories"]) > 5:
            preview_cats += f" (+{len(sec['categories']) - 5} more)"
        lines.append(
            f"- [{sec['title']['en']}]({base}/llms/{sec['id']}.md): "
            f"{cnt} entries across {len(sec['categories'])} categories ({preview_cats})."
        )

    lines.extend(["", "## Directory Categories", ""])
    for sec in catalog["sections"]:
        if sec["id"] not in DIRECTORY_SECTION_IDS:
            continue
        for cat in sec["categories"]:
            if cat["id"] in EXCLUDED_DIRECTORY_CATEGORIES:
                continue
            valid_cnt = sum(
                1 for e in cat["entries"] if e["kind"] == "item" and e.get("url")
            )
            if not valid_cnt:
                continue
            lines.append(
                f"- [{sec['title']['en']} / {cat['title']['en']}]({base}/?section={sec['id']}&category={cat['slug']}): "
                f"{valid_cnt} downloadable items."
            )

    lines.extend(
        [
            "",
            "## Optional",
            "",
            "- [Canonical Markdown Source (English)](https://github.com/agmmnn/awesome-blender/blob/master/README.md): Upstream curated README list.",
            "- [Canonical Markdown Source (Chinese)](https://github.com/agmmnn/awesome-blender/blob/master/README_ZH.md): Synchronized Simplified Chinese edition.",
            "- [Contributing Guidelines](https://github.com/agmmnn/awesome-blender/blob/master/CONTRIBUTING.md): Submission rules and formatting standards.",
            f"- [XML Sitemap]({base}/sitemap.xml): Bilingual `hreflang` sitemap for indexable directory views.",
            "",
        ]
    )
    return "\n".join(lines)


def build_llms_full_txt(catalog: dict[str, Any], site_url: str) -> str:
    """Generate the complete plain-Markdown catalog file (`llms-full.txt`)."""
    base = site_url.rstrip("/")
    st = catalog["stats"]
    header = [
        "# Awesome Blender — Full Catalog",
        "",
        (
            f"> Complete plain-Markdown index of {st['totalEntries']} curated Blender add-ons, "
            f"AI & MCP workflows, 3D assets, standalone tools, tutorials, and community links "
            f"({st['freeEntries']} free, {st['paidEntries']} paid, {st['uniqueGithubRepos']} GitHub repos, "
            f"{st['uniqueBlenderExtensions']} Blender Extensions). Index: {base}/llms.txt"
        ),
        "",
    ]
    body = [
        build_llms_section_md(sec, site_url, heading_level=2).rstrip()
        for sec in catalog["sections"]
    ]
    return "\n".join(header) + "\n\n".join(body) + "\n"


def sync_added_dates(catalog: dict[str, Any]) -> dict[str, str]:
    """Attach `addedAt` dates to catalog items from added_dates.json, auto-stamping new URLs."""
    existing: dict[str, str] = {}
    if OUTPUT_ADDED_DATES_JSON.exists():
        try:
            existing = json.loads(OUTPUT_ADDED_DATES_JSON.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    today = date.today().isoformat()
    updated: dict[str, str] = {}

    for sec in catalog["sections"]:
        for cat in sec["categories"]:
            for entry in cat["entries"]:
                url = entry.get("url")
                if entry.get("kind") == "item" and url:
                    dt = existing.get(url) or today
                    updated[url] = dt
                    entry["addedAt"] = dt
                else:
                    entry["addedAt"] = None

    return {k: updated[k] for k in sorted(updated.keys(), key=str.lower)}


def _collect_recent_items(
    catalog: dict[str, Any], limit: int = RECENT_MD_LIMIT
) -> list[dict[str, Any]]:
    """Collect the latest `limit` directory items ordered by addedAt desc, then README line asc."""
    used_slugs: set[str] = set()
    items: list[dict[str, Any]] = []

    for sec in catalog["sections"]:
        if sec["id"] not in DIRECTORY_SECTION_IDS:
            continue
        for cat in sec["categories"]:
            if cat["id"] in EXCLUDED_DIRECTORY_CATEGORIES:
                continue
            for entry in cat["entries"]:
                if entry.get("kind") != "item" or not entry.get("url"):
                    continue
                base_slug = re.sub(r"^L\d+-", "", entry["id"]) or entry["id"]
                slug = base_slug
                if slug in used_slugs:
                    slug = f"{base_slug}-{cat['slug']}"
                if slug in used_slugs:
                    slug = entry["id"].lower()
                used_slugs.add(slug)
                items.append(
                    {
                        "slug": slug,
                        "title": entry["title"]["en"],
                        "titleZh": entry["title"]["zh"],
                        "url": entry["url"],
                        "description": entry["description"]["en"],
                        "descriptionZh": entry["description"]["zh"],
                        "sectionEmoji": sec.get("emoji") or "",
                        "sectionTitle": sec["title"]["en"],
                        "sectionTitleZh": sec["title"]["zh"],
                        "categoryTitle": cat["title"]["en"],
                        "categoryTitleZh": cat["title"]["zh"],
                        "addedAt": entry.get("addedAt") or "",
                        "line": entry["line"],
                    }
                )

    items.sort(key=lambda x: (x["addedAt"], -x["line"]), reverse=True)
    return items[:limit]


def _extract_toc_anchors(path: Path) -> dict[str, str]:
    """Read exact GitHub heading anchor hrefs from the README Table of Contents (section-scoped)."""
    text = path.read_text(encoding="utf-8")
    anchors: dict[str, str] = {}
    cur_sec = ""
    for line in text.splitlines():
        if "</details>" in line:
            break
        m = re.search(r'<a href="(#[^"]+)">([^<]+)</a>', line)
        if not m:
            continue
        href, label = m.group(1), html.unescape(m.group(2)).strip()
        _, title, _ = split_heading_emoji(label)
        key_title = (title or label).lower()
        indent = len(line) - len(line.lstrip())
        if indent <= 4:
            cur_sec = key_title
            anchors.setdefault(key_title, href)
        else:
            anchors[f"{cur_sec}|{key_title}"] = href
            anchors.setdefault(key_title, href)
    return anchors


def _fallback_github_anchor(title: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", title.lower()).strip().replace(" ", "-")
    return f"#-{slug}"


def build_recent_md(
    catalog: dict[str, Any], site_url: str, limit: int = RECENT_MD_LIMIT
) -> str:
    """Generate RECENT.md showing the latest `limit` curated additions grouped by date."""
    base = site_url.rstrip("/")
    recent = _collect_recent_items(catalog, limit=limit)
    en_anchors = _extract_toc_anchors(README_EN)
    lines = [
        "# ✨ Recently Added to Awesome Blender",
        "",
        (
            f"> Latest {len(recent)} curated additions to [Awesome Blender](README.md) "
            f"(auto-generated, capped at {limit} entries). "
            f"Browse interactively at [Web Directory]({base}/?sort=added) · "
            f"[RSS Feed]({base}/feed.xml)"
        ),
        "",
    ]

    grouped: list[tuple[str, list[dict[str, Any]]]] = []
    for item in recent:
        dt = item["addedAt"] or "Unknown"
        if not grouped or grouped[-1][0] != dt:
            grouped.append((dt, [item]))
        else:
            grouped[-1][1].append(item)

    for dt, group_items in grouped:
        lines.append(f"## {dt} · {len(group_items)} new")
        lines.append("")
        for item in group_items:
            sec_prefix = f"{item['sectionEmoji']} " if item["sectionEmoji"] else ""
            sec_title = item["sectionTitle"]
            cat_title = item["categoryTitle"]
            cat_label = f"{sec_prefix}{sec_title} · {cat_title}"
            anchor = (
                en_anchors.get(f"{sec_title.lower()}|{cat_title.lower()}")
                or en_anchors.get(cat_title.lower())
                or _fallback_github_anchor(cat_title)
            )
            desc = item["description"].strip()
            desc_clean = re.sub(r"\s+", " ", desc)
            detail_url = f"{base}/#{item['slug']}"
            bullet = f"- **[{item['title']}]({item['url']})** ([`{cat_label}`](README.md{anchor}))"
            if desc_clean:
                bullet += f" — {desc_clean}"
            bullet += f" · [Details]({detail_url})"
            lines.append(bullet)
        lines.append("")

    return "\n".join(lines)


def build_feed_xml(
    catalog: dict[str, Any], site_url: str, limit: int = FEED_LIMIT
) -> str:
    """Generate an RSS 2.0 feed (`public/feed.xml`) of the latest `limit` additions."""
    base = site_url.rstrip("/")
    feed_url = f"{base}/feed.xml"
    recent = _collect_recent_items(catalog, limit=limit)

    def to_rfc2822(iso_date: str) -> str:
        try:
            y, m, d = (int(p) for p in iso_date.split("-")[:3])
            dt = datetime(y, m, d, 12, 0, 0, tzinfo=timezone.utc)
        except Exception:
            dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        return format_datetime(dt, usegmt=True)

    latest_pub = to_rfc2822(recent[0]["addedAt"]) if recent else to_rfc2822("")

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        "    <title>Awesome Blender — Recently Added</title>",
        f"    <link>{html.escape(base + '/?sort=added', quote=True)}</link>",
        f'    <atom:link href="{html.escape(feed_url, quote=True)}" rel="self" type="application/rss+xml" />',
        "    <description>Latest curated Blender add-ons, AI &amp; MCP tools, 3D assets, standalone software, tutorials, and community links.</description>",
        "    <language>en</language>",
        f"    <lastBuildDate>{latest_pub}</lastBuildDate>",
    ]

    for item in recent:
        item_link = f"{base}/#{item['slug']}"
        category = f"{item['sectionTitle']} / {item['categoryTitle']}"
        desc_text = item["description"].strip() or f"{item['title']} ({category})"
        desc_full = f"{desc_text} — {item['url']}"
        lines.extend(
            [
                "    <item>",
                f"      <title>{html.escape(item['title'])}</title>",
                f"      <link>{html.escape(item['url'], quote=True)}</link>",
                f'      <guid isPermaLink="true">{html.escape(item_link, quote=True)}</guid>',
                f"      <category>{html.escape(category)}</category>",
                f"      <pubDate>{to_rfc2822(item['addedAt'])}</pubDate>",
                f"      <description>{html.escape(desc_full)}</description>",
                "    </item>",
            ]
        )

    lines.extend(["  </channel>", "</rss>"])
    return "\n".join(lines) + "\n"


def build_directory_lite(catalog: dict[str, Any]) -> dict[str, Any]:
    """Build a minimal, minified subset of catalog.json for fast web UI bundling."""
    entry_fields = (
        "id",
        "line",
        "sectionId",
        "categoryId",
        "subgroupId",
        "subgroup",
        "title",
        "url",
        "description",
        "secondaryLinks",
        "isPaid",
        "isFree",
        "licenses",
        "mediaType",
        "platforms",
        "githubRepo",
        "blenderExtensionId",
        "addedAt",
    )
    lite_sections = []
    for sec in catalog["sections"]:
        if sec["id"] not in DIRECTORY_SECTION_IDS:
            continue
        lite_categories = []
        for cat in sec["categories"]:
            if cat["id"] in EXCLUDED_DIRECTORY_CATEGORIES:
                continue
            valid_entries = [
                {k: e[k] for k in entry_fields if k in e}
                for e in cat["entries"]
                if e.get("kind") == "item" and e.get("url")
            ]
            if not valid_entries:
                continue
            active_sg_ids = {
                e["subgroupId"] for e in valid_entries if e.get("subgroupId")
            }
            valid_subgroups = [
                {"id": sg["id"], "line": sg["line"], "title": sg["title"], "url": sg.get("url"), "mediaType": sg.get("mediaType")}
                for sg in cat["subgroups"]
                if sg["id"] in active_sg_ids
            ]
            lite_categories.append(
                {
                    "id": cat["id"],
                    "slug": cat["slug"],
                    "sectionId": cat["sectionId"],
                    "line": cat["line"],
                    "emoji": cat["emoji"],
                    "title": cat["title"],
                    "subgroups": valid_subgroups,
                    "entries": valid_entries,
                }
            )
        lite_sections.append(
            {
                "id": sec["id"],
                "line": sec["line"],
                "emoji": sec["emoji"],
                "title": sec["title"],
                "categories": lite_categories,
            }
        )
    return {"sections": lite_sections}


def _truncate_text(text: str, max_len: int) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= max_len:
        return clean
    cut = clean[: max_len - 1].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return f"{cut}…"


_SHORT_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def _format_short_month_day(iso_date: str, lang: str = "en") -> str:
    parts = iso_date.split("-")
    if len(parts) < 3:
        return iso_date
    try:
        month = int(parts[1])
        day = int(parts[2])
    except ValueError:
        return iso_date
    if not (1 <= month <= 12):
        return iso_date
    if lang == "zh":
        return f"{month}月{day}日"
    return f"{_SHORT_MONTHS[month - 1]} {day}"


def build_readme_recent_block(
    catalog: dict[str, Any],
    site_url: str,
    lang: str = "en",
    limit: int = README_RECENT_LIMIT,
) -> str:
    """Build the compact auto-updated Recently Added section for README.md / README_ZH.md."""
    recent = _collect_recent_items(catalog, limit=limit)
    header = (
        "### [✨ 最近新增](RECENT.md)"
        if lang == "zh"
        else "### [✨ Recently Added](RECENT.md)"
    )

    anchors = _extract_toc_anchors(README_ZH if lang == "zh" else README_EN)
    lines = [RECENT_START_MARKER, "", header, ""]
    for item in recent:
        title = item["titleZh"] if lang == "zh" else item["title"]
        sec_title = item["sectionTitleZh"] if lang == "zh" else item["sectionTitle"]
        cat_title = item["categoryTitleZh"] if lang == "zh" else item["categoryTitle"]
        anchor = (
            anchors.get(f"{sec_title.lower()}|{cat_title.lower()}")
            or anchors.get(cat_title.lower())
            or _fallback_github_anchor(cat_title)
        )
        desc_raw = item["descriptionZh"] if lang == "zh" else item["description"]
        dt_short = _format_short_month_day(item["addedAt"], lang) if item["addedAt"] else ""
        date_suffix = f" _({dt_short})_" if dt_short else ""
        # Budget description length so each bullet (including date) stays cleanly on a single line
        used_len = len(title) + len(cat_title) + (len(dt_short) + 3 if dt_short else 0)
        max_desc = max(20, (44 if lang == "zh" else 92) - used_len)
        desc = _truncate_text(desc_raw, max_desc)
        desc_part = f" — {desc}" if desc else ""
        lines.append(
            f"- **[{title}]({item['url']})** [`{cat_title}`]({anchor}){desc_part}{date_suffix}"
        )
    lines.extend(["", RECENT_END_MARKER])
    return "\n".join(lines)


def align_readme_zh() -> tuple[bool, int]:
    """
    Align README_ZH.md line-by-line with README.md when contributors edit only README.md.
    Preserves all existing Chinese translations matched by URL, heading emoji, or subgroup
    order within each category, and falls back to the English line for newly added items.
    Returns (changed, fallback_count).
    """
    en_lines = README_EN.read_text(encoding="utf-8").splitlines()
    zh_lines = README_ZH.read_text(encoding="utf-8").splitlines()

    def split_zones(lines: list[str], sym_prefixes: tuple[str, ...]):
        start = next((i for i, l in enumerate(lines) if l.startswith("## ")), len(lines))
        end = next(
            (i for i in range(start, len(lines)) if any(lines[i].startswith(p) for p in sym_prefixes)),
            len(lines),
        )
        return lines[:start], lines[start:end], lines[end:]

    en_pre, en_body, en_post = split_zones(en_lines, ("### Symbols",))
    zh_pre, zh_body, zh_post = split_zones(zh_lines, ("### 符号", "### Symbols"))

    # Quick check: already aligned in count and URL parity?
    if len(en_lines) == len(zh_lines):
        mismatch = False
        for e_l, z_l in zip(en_body, zh_body):
            if URL_RE.findall(e_l) != URL_RE.findall(z_l):
                mismatch = True
                break
        if not mismatch:
            return False, 0

    # Index existing Chinese body lines
    zh_by_urls: dict[tuple[str, ...], str] = {}
    zh_h2_by_emoji: dict[str, str] = {}
    zh_h3_by_emoji: dict[str, str] = {}
    zh_h2_seq: list[str] = []
    zh_h3_by_sec: dict[str, list[str]] = {}
    zh_subgroups_by_cat: dict[str, list[str]] = {}
    zh_notes_by_cat: dict[str, str] = {}

    cur_sec_key = ""
    cur_cat_key = ""
    for line in zh_body:
        stripped = line.rstrip()
        urls = tuple(URL_RE.findall(stripped))
        if urls and stripped not in ("", "---") and 'href="#table"' not in stripped:
            zh_by_urls.setdefault(urls, stripped)

        if stripped.startswith("## "):
            em, _, _ = split_heading_emoji(stripped[3:])
            cur_sec_key = em or stripped
            zh_h2_seq.append(stripped)
            if em:
                zh_h2_by_emoji[em] = stripped
            cur_cat_key = ""
        elif stripped.startswith("### "):
            em, _, _ = split_heading_emoji(stripped[4:])
            cur_cat_key = f"{cur_sec_key}|{em or stripped}"
            zh_h3_by_sec.setdefault(cur_sec_key, []).append(stripped)
            if em:
                zh_h3_by_emoji[f"{cur_sec_key}|{em}"] = stripped
        elif (
            stripped.startswith("- ")
            and (stripped.endswith("：") or stripped.endswith(":"))
            and "](" not in stripped
        ):
            zh_subgroups_by_cat.setdefault(cur_cat_key, []).append(stripped)
        elif stripped.startswith("_") and stripped.endswith("_") and "](" not in stripped:
            zh_notes_by_cat[cur_cat_key] = stripped

    aligned_body: list[str] = []
    fallback_count = 0
    sec_idx = 0
    cat_idx_in_sec: dict[str, int] = {}
    sg_idx_in_cat: dict[str, int] = {}
    cur_en_sec_key = ""
    cur_en_cat_key = ""

    for line in en_body:
        s = line.rstrip()
        if not s:
            aligned_body.append("")
            continue
        if s == "---":
            aligned_body.append("---")
            continue
        if 'href="#table"' in s:
            aligned_body.append('<p align="right"><sub><a href="#table">↑ 返回顶部</a></sub></p>')
            continue

        urls = tuple(URL_RE.findall(s))
        if urls and s in zh_by_urls.values():
            aligned_body.append(s)
            continue
        if urls and urls in zh_by_urls:
            aligned_body.append(zh_by_urls[urls])
            continue

        if s.startswith("## "):
            em, _, _ = split_heading_emoji(s[3:])
            cur_en_sec_key = em or s
            matched = zh_h2_by_emoji.get(em or "") or (
                zh_h2_seq[sec_idx] if sec_idx < len(zh_h2_seq) else None
            )
            sec_idx += 1
            cur_en_cat_key = ""
            if matched:
                aligned_body.append(matched)
            else:
                aligned_body.append(s)
                fallback_count += 1
            continue

        if s.startswith("### "):
            em, _, _ = split_heading_emoji(s[4:])
            cur_en_cat_key = f"{cur_en_sec_key}|{em or s}"
            c_idx = cat_idx_in_sec.get(cur_en_sec_key, 0)
            cat_idx_in_sec[cur_en_sec_key] = c_idx + 1
            sec_h3s = zh_h3_by_sec.get(cur_en_sec_key, [])
            matched = zh_h3_by_emoji.get(f"{cur_en_sec_key}|{em}") or (
                sec_h3s[c_idx] if c_idx < len(sec_h3s) else None
            )
            if matched:
                aligned_body.append(matched)
            else:
                aligned_body.append(s)
                fallback_count += 1
            continue

        if s.startswith("- ") and s.endswith(":") and "](" not in s:
            sg_list = zh_subgroups_by_cat.get(cur_en_cat_key, [])
            sg_i = sg_idx_in_cat.get(cur_en_cat_key, 0)
            sg_idx_in_cat[cur_en_cat_key] = sg_i + 1
            if sg_i < len(sg_list):
                aligned_body.append(sg_list[sg_i])
            else:
                aligned_body.append(s)
                fallback_count += 1
            continue

        if s.startswith("_") and s.endswith("_") and "](" not in s:
            if cur_en_cat_key in zh_notes_by_cat:
                aligned_body.append(zh_notes_by_cat[cur_en_cat_key])
            else:
                aligned_body.append(s)
                fallback_count += 1
            continue

        # HTML structural lines, comments, or newly added English items without ZH translation yet
        aligned_body.append(s)
        if urls:
            fallback_count += 1

    new_zh_lines = zh_pre + aligned_body + zh_post
    new_zh_text = "\n".join(new_zh_lines) + "\n"
    if new_zh_text == README_ZH.read_text(encoding="utf-8"):
        return False, fallback_count

    README_ZH.write_text(new_zh_text, encoding="utf-8")
    return True, fallback_count


def apply_readme_recent_block(path: Path, block: str) -> str:
    """Replace the <!-- RECENT:START --> ... <!-- RECENT:END --> block inside a README file."""
    content = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"{re.escape(RECENT_START_MARKER)}.*?{re.escape(RECENT_END_MARKER)}",
        re.DOTALL,
    )
    if not pattern.search(content):
        return content
    return pattern.sub(lambda _: block, content, count=1)


def _verify_text_output(path: Path, expected: str) -> str | None:
    """Return an error message if a generated file is missing or out of sync."""
    if not path.exists() or path.read_text(encoding="utf-8") != expected:
        return (
            f"❌ {path.relative_to(ROOT_DIR)} is out of sync. "
            "Run `python3 web/scripts/build_catalog.py`."
        )
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build data/catalog.json from READMEs.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate lossless parsing and parity without writing or if out-of-date.",
    )
    parser.add_argument(
        "--align-zh",
        action="store_true",
        help="Auto-align README_ZH.md to README.md (English fallback for new lines) before building.",
    )
    parser.add_argument(
        "--site-url",
        default=os.environ.get("SITE_URL", "https://awesome-blender.vercel.app"),
        help="Base URL used in sitemap.xml and llms.txt",
    )
    args = parser.parse_args()

    if args.align_zh and not args.check:
        changed, fallback_count = align_readme_zh()
        if changed:
            print(
                f"🔄 Auto-aligned README_ZH.md with README.md ({fallback_count} English fallback line(s))."
            )

    catalog, errors = build_catalog()
    if errors:
        print("❌ Catalog build failed with errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    added_dates = sync_added_dates(catalog)
    rendered_added_dates = json.dumps(added_dates, ensure_ascii=False, indent=2) + "\n"
    rendered = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    rendered_lite = (
        json.dumps(
            build_directory_lite(catalog), ensure_ascii=False, separators=(",", ":")
        )
        + "\n"
    )
    rendered_public_json = json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n"
    rendered_sitemap = build_sitemap_xml(catalog, args.site_url)
    rendered_feed = build_feed_xml(catalog, args.site_url)
    rendered_recent_md = build_recent_md(catalog, args.site_url)
    rendered_readme_en = apply_readme_recent_block(
        README_EN, build_readme_recent_block(catalog, args.site_url, lang="en")
    )
    rendered_readme_zh = apply_readme_recent_block(
        README_ZH, build_readme_recent_block(catalog, args.site_url, lang="zh")
    )
    rendered_llms = build_llms_txt(catalog, args.site_url)
    rendered_llms_full = build_llms_full_txt(catalog, args.site_url)
    section_outputs = {
        OUTPUT_LLMS_DIR / f"{sec['id']}.md": build_llms_section_md(
            sec, args.site_url, heading_level=1
        )
        for sec in catalog["sections"]
    }

    expected_files: list[tuple[Path, str]] = [
        (README_EN, rendered_readme_en),
        (README_ZH, rendered_readme_zh),
        (OUTPUT_ADDED_DATES_JSON, rendered_added_dates),
        (OUTPUT_JSON, rendered),
        (OUTPUT_LITE_JSON, rendered_lite),
        (OUTPUT_PUBLIC_JSON, rendered_public_json),
        (OUTPUT_SITEMAP, rendered_sitemap),
        (OUTPUT_FEED_XML, rendered_feed),
        (OUTPUT_RECENT_MD, rendered_recent_md),
        (OUTPUT_LLMS_TXT, rendered_llms),
        (OUTPUT_LLMS_FULL_TXT, rendered_llms_full),
        *section_outputs.items(),
    ]

    if args.check:
        for path, content in expected_files:
            err = _verify_text_output(path, content)
            if err:
                print(err, file=sys.stderr)
                return 1
        if OUTPUT_LLMS_DIR.exists():
            expected_names = {p.name for p in section_outputs}
            stale = [p.name for p in OUTPUT_LLMS_DIR.glob("*.md") if p.name not in expected_names]
            if stale:
                print(
                    f"❌ Stale section files in {OUTPUT_LLMS_DIR.relative_to(ROOT_DIR)}: {stale}",
                    file=sys.stderr,
                )
                return 1
        print(
            f"✅ {OUTPUT_JSON.relative_to(ROOT_DIR)}, catalog.json, sitemap.xml, and llms.txt bundle are up-to-date and 100% lossless."
        )
        return 0

    OUTPUT_LLMS_DIR.mkdir(parents=True, exist_ok=True)
    expected_names = {p.name for p in section_outputs}
    for old_file in OUTPUT_LLMS_DIR.glob("*.md"):
        if old_file.name not in expected_names:
            old_file.unlink()

    for path, content in expected_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    st = catalog["stats"]
    print(
        f"✅ Built {OUTPUT_JSON.relative_to(ROOT_DIR)}, public/catalog.json, sitemap.xml, and llms.txt bundle:\n"
        f"   Sections: {st['totalSections']} | Categories: {st['totalCategories']} | Subgroups: {st['totalSubgroups']}\n"
        f"   Entries:  {st['totalEntries']} {st['entryKinds']}\n"
        f"   URLs:     {st['totalContentUrls']} total ({st['uniqueContentUrls']} unique) — 100% lossless\n"
        f"   GitHub Repos: {st['uniqueGithubRepos']} | Blender Extensions: {st['uniqueBlenderExtensions']}\n"
        f"   Licenses: {st['licenseCounts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
