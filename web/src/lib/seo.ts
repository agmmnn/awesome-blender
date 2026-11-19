import {
  DIRECTORY_DATA,
  type DirectoryItem,
  type DirectorySectionId,
  type DirectorySortId,
  type Locale,
} from "@/lib/catalog";

export const SITE_NAME = "Awesome Blender";
export const SITE_URL = (
  import.meta.env.VITE_SITE_URL || "https://awesome-blender.vercel.app"
).replace(/\/+$/, "");
export const OG_IMAGE_URL = `${SITE_URL}/og-image.jpg`;

export interface SeoFilterInput {
  section?: "all" | DirectorySectionId;
  category?: string;
  subgroup?: string;
  q?: string;
  price?: "all" | "free" | "paid";
  platform?:
    | "all"
    | "extensions"
    | "github"
    | "open-source"
    | "superhive"
    | "gumroad";
  license?: "all" | "gpl" | "mit" | "zero" | "cc";
  recent?: boolean;
  sort?: DirectorySortId;
  lang?: Locale;
}

export function filterDirectoryItems(
  input: SeoFilterInput,
  searchOverride?: string
): DirectoryItem[] {
  const activeSection = input.section ?? "all";
  const activeCategory = input.category ?? "all";
  const activeSubgroup = input.subgroup ?? "all";
  const activePrice = input.price ?? "all";
  const activePlatform = input.platform ?? "all";
  const activeLicense = input.license ?? "all";
  const activeRecent = Boolean(input.recent);
  const activeSort = input.sort ?? "curated";
  const lang: Locale = input.lang === "zh" ? "zh" : "en";
  const qLower = (searchOverride ?? input.q ?? "").trim().toLowerCase();

  const filtered = DIRECTORY_DATA.items.filter((item) => {
    if (activeRecent && !item.isNew) return false;
    if (activeSection !== "all" && item.sectionId !== activeSection) {
      return false;
    }
    if (activeCategory !== "all" && item.categorySlug !== activeCategory) {
      return false;
    }
    if (activeSubgroup !== "all" && item.subgroupId !== activeSubgroup) {
      return false;
    }
    if (activePrice === "free" && !item.isFree) return false;
    if (activePrice === "paid" && !item.isPaid) return false;

    if (activePlatform !== "all" && !item.platforms.includes(activePlatform)) {
      return false;
    }

    if (activeLicense !== "all") {
      if (activeLicense === "cc") {
        if (!item.licenses.includes("cc") && !item.licenses.includes("by")) {
          return false;
        }
      } else if (!item.licenses.includes(activeLicense)) {
        return false;
      }
    }

    if (qLower && !item.searchText.includes(qLower)) {
      return false;
    }

    return true;
  });

  if (activeSort === "curated") {
    return filtered;
  }

  return [...filtered].sort((a, b) => {
    if (activeSort === "added") {
      const aAdded = a.addedAt ?? "";
      const bAdded = b.addedAt ?? "";
      if (bAdded !== aAdded) return bAdded.localeCompare(aAdded);
      return a.line - b.line;
    }
    if (activeSort === "stars") {
      const aStars = a.githubStars ?? -1;
      const bStars = b.githubStars ?? -1;
      if (bStars !== aStars) return bStars - aStars;
      return a.line - b.line;
    }
    if (activeSort === "updated") {
      const aDate = a.githubPushedAt ?? "";
      const bDate = b.githubPushedAt ?? "";
      if (bDate !== aDate) return bDate.localeCompare(aDate);
      return a.line - b.line;
    }
    if (activeSort === "name") {
      const aTitle = a.title[lang] || a.title.en;
      const bTitle = b.title[lang] || b.title.en;
      return aTitle.localeCompare(bTitle);
    }
    if (activeSort === "free") {
      const aScore = a.licenses.length > 0 ? 2 : a.isFree ? 1 : 0;
      const bScore = b.licenses.length > 0 ? 2 : b.isFree ? 1 : 0;
      if (bScore !== aScore) return bScore - aScore;
      return a.line - b.line;
    }
    if (activeSort === "extensions") {
      const aScore =
        a.platforms.includes("extensions") || a.blenderExtensionId
          ? 2
          : a.platforms.includes("open-source") || a.githubRepo
            ? 1
            : 0;
      const bScore =
        b.platforms.includes("extensions") || b.blenderExtensionId
          ? 2
          : b.platforms.includes("open-source") || b.githubRepo
            ? 1
            : 0;
      if (bScore !== aScore) return bScore - aScore;
      return a.line - b.line;
    }
    return 0;
  });
}

function buildCanonicalQueryUrl(
  params: Pick<SeoFilterInput, "section" | "category" | "lang">,
  langOverride?: Locale
): string {
  const sp = new URLSearchParams();
  if (params.section && params.section !== "all") {
    sp.set("section", params.section);
  }
  if (params.category && params.category !== "all") {
    sp.set("category", params.category);
  }
  const effectiveLang = langOverride ?? params.lang;
  if (effectiveLang === "zh") {
    sp.set("lang", "zh");
  }
  const qs = sp.toString();
  return qs ? `${SITE_URL}/?${qs}` : `${SITE_URL}/`;
}

export function buildDirectorySeo(input: SeoFilterInput) {
  const lang: Locale = input.lang === "zh" ? "zh" : "en";
  const activeSection = input.section ?? "all";
  const activeCategory = input.category ?? "all";
  const activeSubgroup = input.subgroup ?? "all";
  const q = input.q?.trim() ?? "";

  const sectionObj =
    activeSection !== "all"
      ? DIRECTORY_DATA.sections.find((s) => s.id === activeSection) ?? null
      : null;

  const categoryObj =
    activeCategory !== "all"
      ? DIRECTORY_DATA.categories.find(
          (c) =>
            c.slug === activeCategory &&
            (activeSection === "all" || c.sectionId === activeSection)
        ) ?? null
      : null;

  const subgroupObj =
    categoryObj && activeSubgroup !== "all"
      ? categoryObj.subgroups.find((sg) => sg.id === activeSubgroup) ?? null
      : null;

  const matchedItems = filterDirectoryItems(input);
  const count = matchedItems.length;

  // Determine whether this view should be indexed or marked noindex (search/multi-facet combinations)
  const hasFacetNoise =
    Boolean(q) ||
    Boolean(input.subgroup) ||
    Boolean(input.recent) ||
    (input.price && input.price !== "all") ||
    (input.platform && input.platform !== "all") ||
    (input.license && input.license !== "all");

  const robotsContent = hasFacetNoise
    ? "noindex, follow"
    : "index, follow, max-image-preview:large, max-snippet:-1";

  const canonicalSection =
    sectionObj?.id ?? categoryObj?.sectionId ?? undefined;
  const canonicalCategory = categoryObj?.slug ?? undefined;

  const canonicalUrl = buildCanonicalQueryUrl({
    section: canonicalSection,
    category: canonicalCategory,
    lang,
  });
  const enAlternateUrl = buildCanonicalQueryUrl(
    { section: canonicalSection, category: canonicalCategory },
    "en"
  );
  const zhAlternateUrl = buildCanonicalQueryUrl(
    { section: canonicalSection, category: canonicalCategory },
    "zh"
  );

  // Page Title, H1 Heading & Description tailored to context
  let heading =
    lang === "zh"
      ? "Awesome Blender 精选目录"
      : "Awesome Blender Directory";
  let subtitle =
    lang === "zh"
      ? "精心整理的 Blender 插件、AI & MCP 工具、3D 资产、HDRI、独立软件、教程与社区资源目录。"
      : "Curated Blender add-ons, AI & MCP tools, 3D assets, HDRIs, standalone software, tutorials, and community hubs.";
  let title =
    lang === "zh"
      ? `${SITE_NAME} — ${DIRECTORY_DATA.totalCount} 个精选 Blender 插件、AI & MCP 与 3D 资产目录`
      : `${SITE_NAME} — ${DIRECTORY_DATA.totalCount} Curated Blender Add-ons, AI & MCP & 3D Tools`;
  let description = subtitle;

  if (q) {
    heading =
      lang === "zh" ? `“${q}” 的搜索结果` : `Search results for “${q}”`;
    subtitle =
      lang === "zh"
        ? `在 Awesome Blender 目录中找到 ${count} 个匹配“${q}”的插件或资源。`
        : `Found ${count} Blender add-ons, assets, or tools matching “${q}”.`;
    title =
      lang === "zh"
        ? `搜索：${q} — ${SITE_NAME}`
        : `Search “${q}” — ${SITE_NAME} Directory`;
    description = subtitle;
  } else if (categoryObj) {
    const catName = categoryObj.title[lang] || categoryObj.title.en;
    const secName =
      DIRECTORY_DATA.sections.find((s) => s.id === categoryObj.sectionId)
        ?.title[lang] ?? "";
    const sgName = subgroupObj
      ? subgroupObj.title[lang] || subgroupObj.title.en
      : null;

    heading = sgName ? `${catName} · ${sgName}` : catName;
    subtitle =
      lang === "zh"
        ? `${secName}分类下精选的优质 Blender 资源、工具与指南。`
        : `Curated Blender tools, assets, and guides in ${sgName ? `${sgName} (${catName})` : catName}.`;
    title =
      lang === "zh"
        ? `${heading} (${count}) — ${secName} | ${SITE_NAME}`
        : `${heading} (${count}) — Blender ${secName} | ${SITE_NAME}`;
    description = subtitle;
  } else if (sectionObj) {
    const secName = sectionObj.title[lang] || sectionObj.title.en;
    const isAiSection = sectionObj.id === "ai-mcp";
    const isTutorialsSection = sectionObj.id === "tutorials";
    const isSocialSection = sectionObj.id === "social";
    heading = isAiSection
      ? "Blender AI & MCP"
      : `Blender ${secName}`;
    subtitle = isAiSection
      ? lang === "zh"
        ? "精选 Blender AI、MCP 服务器、智能体、生成式 3D 与评测工具。"
        : "Curated Blender AI, MCP server, agent, generative 3D, and benchmark tools."
      : isTutorialsSection
        ? lang === "zh"
          ? "精选 Blender 入门指南、视频教程、播放列表、官方文档与进阶课程。"
          : "Curated Blender getting-started guides, video tutorials, playlists, official documentation, and courses."
        : isSocialSection
          ? lang === "zh"
            ? "精选 Blender 社区论坛、YouTube 频道、技术博客、3D 赛事挑战与艺术作品平台。"
            : "Curated Blender communities, YouTube channels, technical blogs, challenges, and artwork showcases."
          : lang === "zh"
            ? `精选可下载的 Blender ${secName}。支持按开源协议、平台与价格筛选。`
            : `Curated downloadable Blender ${secName.toLowerCase()}. Filter by license, platform, and pricing.`;
    title =
      lang === "zh"
        ? `Blender ${secName} (${count}) — ${SITE_NAME}`
        : `Blender ${secName} (${count}) — ${SITE_NAME} Directory`;
    description = subtitle;
  }

  // Schema.org BreadcrumbList
  const breadcrumbItems: Array<{
    "@type": "ListItem";
    position: number;
    name: string;
    item: string;
  }> = [
    {
      "@type": "ListItem",
      position: 1,
      name: SITE_NAME,
      item: enAlternateUrl === zhAlternateUrl ? enAlternateUrl : buildCanonicalQueryUrl({}, lang),
    },
  ];

  if (canonicalSection) {
    const sec = DIRECTORY_DATA.sections.find((s) => s.id === canonicalSection);
    if (sec) {
      breadcrumbItems.push({
        "@type": "ListItem",
        position: breadcrumbItems.length + 1,
        name: sec.title[lang] || sec.title.en,
        item: buildCanonicalQueryUrl({ section: sec.id, lang }),
      });
    }
  }

  if (categoryObj) {
    breadcrumbItems.push({
      "@type": "ListItem",
      position: breadcrumbItems.length + 1,
      name: categoryObj.title[lang] || categoryObj.title.en,
      item: canonicalUrl,
    });
  }

  // Schema.org JSON-LD Graph (WebSite + SearchAction, CollectionPage, ItemList, BreadcrumbList)
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebSite",
        "@id": `${SITE_URL}/#website`,
        url: `${SITE_URL}/`,
        name: SITE_NAME,
        description:
          "Curated directory of downloadable Blender add-ons, official extensions, 3D assets, HDRIs, and standalone tools.",
        inLanguage: ["en", "zh"],
        potentialAction: {
          "@type": "SearchAction",
          target: {
            "@type": "EntryPoint",
            urlTemplate: `${SITE_URL}/?q={search_term_string}`,
          },
          "query-input": "required name=search_term_string",
        },
      },
      {
        "@type": "CollectionPage",
        "@id": `${canonicalUrl}#collection`,
        url: canonicalUrl,
        name: heading,
        description,
        inLanguage: lang === "zh" ? "zh-CN" : "en-US",
        isPartOf: { "@id": `${SITE_URL}/#website` },
        mainEntity: {
          "@type": "ItemList",
          numberOfItems: count,
          itemListElement: matchedItems.slice(0, 24).map((item, idx) => ({
            "@type": "ListItem",
            position: idx + 1,
            name: item.title[lang] || item.title.en,
            description: item.description[lang] || item.description.en,
            url: item.url ?? canonicalUrl,
          })),
        },
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: breadcrumbItems,
      },
    ],
  };

  return {
    lang,
    heading,
    subtitle,
    title,
    description,
    robotsContent,
    canonicalUrl,
    enAlternateUrl,
    zhAlternateUrl,
    matchedItems,
    jsonLd,
  };
}
