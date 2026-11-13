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
from pathlib import Path
from typing import Any

WEB_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = WEB_DIR.parent
README_EN = ROOT_DIR / "README.md"
README_ZH = ROOT_DIR / "README_ZH.md"
OUTPUT_JSON = WEB_DIR / "src" / "data" / "catalog.json"
OUTPUT_SITEMAP = WEB_DIR / "public" / "sitemap.xml"

DIRECTORY_SECTION_IDS = {"add-ons", "resources", "standalone"}
EXCLUDED_DIRECTORY_CATEGORIES = {
    "resources/art-reference",
    "resources/useful",
    "resources/free-stocks",
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
    Extract `[$]`, `repo`, `market`, and license badges (`gpl`, `mit`, `zero`, `cc`, `by`, `nc`)
    from a markdown string, returning the cleaned markdown and badge metadata.
    """
    s = text
    is_paid = False
    if "[$]" in s:
        is_paid = True
        s = re.sub(r"\s*\[\$\]\s*", " ", s)

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Build data/catalog.json from READMEs.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate lossless parsing and parity without writing or if out-of-date.",
    )
    parser.add_argument(
        "--site-url",
        default=os.environ.get("SITE_URL", "https://awesome-blender.vercel.app"),
        help="Base URL used in sitemap.xml",
    )
    args = parser.parse_args()

    catalog, errors = build_catalog()
    if errors:
        print("❌ Catalog build failed with errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_SITEMAP.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    rendered_sitemap = build_sitemap_xml(catalog, args.site_url)

    if args.check:
        if not OUTPUT_JSON.exists():
            print(
                f"❌ {OUTPUT_JSON.relative_to(ROOT_DIR)} does not exist. Run `python3 web/scripts/build_catalog.py`.",
                file=sys.stderr,
            )
            return 1
        current = OUTPUT_JSON.read_text(encoding="utf-8")
        if current != rendered:
            print(
                f"❌ {OUTPUT_JSON.relative_to(ROOT_DIR)} is out of sync with README.md / README_ZH.md. Run `python3 web/scripts/build_catalog.py`.",
                file=sys.stderr,
            )
            return 1
        if not OUTPUT_SITEMAP.exists() or OUTPUT_SITEMAP.read_text(encoding="utf-8") != rendered_sitemap:
            print(
                f"❌ {OUTPUT_SITEMAP.relative_to(ROOT_DIR)} is out of sync. Run `python3 web/scripts/build_catalog.py`.",
                file=sys.stderr,
            )
            return 1
        print(f"✅ {OUTPUT_JSON.relative_to(ROOT_DIR)} and sitemap.xml are up-to-date and 100% lossless.")
        return 0

    OUTPUT_JSON.write_text(rendered, encoding="utf-8")
    OUTPUT_SITEMAP.write_text(rendered_sitemap, encoding="utf-8")

    st = catalog["stats"]
    print(
        f"✅ Built {OUTPUT_JSON.relative_to(ROOT_DIR)} successfully:\n"
        f"   Sections: {st['totalSections']} | Categories: {st['totalCategories']} | Subgroups: {st['totalSubgroups']}\n"
        f"   Entries:  {st['totalEntries']} {st['entryKinds']}\n"
        f"   URLs:     {st['totalContentUrls']} total ({st['uniqueContentUrls']} unique) — 100% lossless\n"
        f"   GitHub Repos: {st['uniqueGithubRepos']} | Blender Extensions: {st['uniqueBlenderExtensions']}\n"
        f"   Licenses: {st['licenseCounts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
