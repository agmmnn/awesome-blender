import rawCatalogJson from "@/data/directory_lite.json";
import rawGithubMetaJson from "@/data/github_meta.json";
import type {
  CatalogCategory,
  CatalogData,
  CatalogEntry,
  CatalogSubgroup,
  LicenseCode,
  Locale,
  LocalizedText,
  PlatformTag,
} from "@/data/schema";

interface GithubRepoMeta {
  stars: number;
  pushedAt: string | null;
  customOgImage: string | null;
  isArchived?: boolean;
}

type LiteCatalogEntry = Omit<CatalogEntry, "kind" | "descriptionMd" | "allUrls"> & {
  kind?: CatalogEntry["kind"];
};

const rawCatalog = rawCatalogJson as unknown as CatalogData;
const githubMetaMap = rawGithubMetaJson as unknown as Record<
  string,
  GithubRepoMeta
>;

export type DirectorySectionId =
  | "add-ons"
  | "ai-mcp"
  | "resources"
  | "standalone"
  | "tutorials"
  | "social";

export type DirectorySortId =
  | "curated"
  | "added"
  | "stars"
  | "updated"
  | "extensions"
  | "free"
  | "name";

const ALLOWED_SECTIONS = new Set<string>([
  "add-ons",
  "ai-mcp",
  "resources",
  "standalone",
  "tutorials",
  "social",
]);

/**
 * Exclude non-downloadable reference/article categories inside Resources
 * so every item in the directory is a downloadable/usable add-on, asset, or tool.
 */
const EXCLUDED_CATEGORY_IDS = new Set<string>([
  "resources/art-reference",
  "resources/related-awesome-lists",
]);

export interface DirectoryItem extends LiteCatalogEntry {
  slug: string;
  sectionId: DirectorySectionId;
  sectionTitle: LocalizedText;
  categoryTitle: LocalizedText;
  categorySlug: string;
  categoryEmoji: string | null;
  addedAt: string | null;
  isNew: boolean;
  githubStars: number | null;
  githubPushedAt: string | null;
  avatarUrl: string | null;
  previewImageUrl: string | null;
  domainLabel: string | null;
  searchText: string;
}

function extractYoutubeVideoId(url: string | null): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.replace(/^www\./, "");
    if (host === "youtu.be") {
      const id = parsed.pathname.slice(1).split("/")[0];
      return id || null;
    }
    if (host === "youtube.com" || host === "m.youtube.com") {
      return parsed.searchParams.get("v");
    }
  } catch {}
  return null;
}

function deriveVisualMeta(entry: CatalogEntry) {
  const ghMeta = entry.githubRepo
    ? githubMetaMap[entry.githubRepo] ?? null
    : null;
  const githubOwner = entry.githubRepo
    ? entry.githubRepo.split("/")[0] || null
    : null;

  let hostname: string | null = null;
  if (entry.url) {
    try {
      hostname = new URL(entry.url).hostname.replace(/^www\./, "");
    } catch {}
  }

  const avatarUrl = githubOwner
    ? `https://github.com/${githubOwner}.png?size=72`
    : hostname
      ? `https://www.google.com/s2/favicons?domain=${hostname}&sz=64`
      : null;

  const ytId = extractYoutubeVideoId(entry.url);
  const previewImageUrl = ytId
    ? `https://i.ytimg.com/vi/${ytId}/hqdefault.jpg`
    : ghMeta?.customOgImage ?? null;

  const domainLabel =
    hostname === "github.com" && entry.githubRepo
      ? entry.githubRepo
      : hostname;

  return {
    githubStars: ghMeta?.stars ?? null,
    githubPushedAt: ghMeta?.pushedAt ?? null,
    avatarUrl,
    previewImageUrl,
    domainLabel,
  };
}

export interface DirectoryCategory {
  id: string;
  slug: string;
  sectionId: DirectorySectionId;
  emoji: string | null;
  title: LocalizedText;
  subgroups: CatalogSubgroup[];
  itemCount: number;
}

export interface DirectorySection {
  id: DirectorySectionId;
  emoji: string | null;
  title: LocalizedText;
  categories: DirectoryCategory[];
  itemCount: number;
}

function buildDirectoryData() {
  const sections: DirectorySection[] = [];
  const categories: DirectoryCategory[] = [];
  const items: DirectoryItem[] = [];
  const usedSlugs = new Set<string>();

  for (const sec of rawCatalog.sections) {
    if (!ALLOWED_SECTIONS.has(sec.id)) continue;
    const sectionId = sec.id as DirectorySectionId;
    const secCategories: DirectoryCategory[] = [];
    let secItemCount = 0;

    for (const cat of sec.categories) {
      if (EXCLUDED_CATEGORY_IDS.has(cat.id)) continue;

      const validEntries = cat.entries.filter(
        (e) => (!e.kind || e.kind === "item") && Boolean(e.url)
      );
      if (validEntries.length === 0) continue;

      const activeSubgroupIds = new Set(
        validEntries.map((e) => e.subgroupId).filter(Boolean)
      );
      const validSubgroups = cat.subgroups.filter((sg) =>
        activeSubgroupIds.has(sg.id)
      );

      const dirCat: DirectoryCategory = {
        id: cat.id,
        slug: cat.slug,
        sectionId,
        emoji: cat.emoji,
        title: cat.title,
        subgroups: validSubgroups,
        itemCount: validEntries.length,
      };

      secCategories.push(dirCat);
      categories.push(dirCat);
      secItemCount += validEntries.length;

      for (const entry of validEntries) {
        const baseSlug = entry.id.replace(/^L\d+-/, "") || entry.id;
        let slug = baseSlug;
        if (usedSlugs.has(slug)) {
          slug = `${baseSlug}-${cat.slug}`;
        }
        if (usedSlugs.has(slug)) {
          slug = entry.id.toLowerCase();
        }
        usedSlugs.add(slug);

        const searchText = [
          entry.title.en,
          entry.title.zh,
          entry.description.en,
          entry.description.zh,
          cat.title.en,
          cat.title.zh,
          entry.subgroup?.en ?? "",
          entry.subgroup?.zh ?? "",
          entry.githubRepo ?? "",
          entry.blenderExtensionId ?? "",
        ]
          .join(" ")
          .toLowerCase();

        items.push({
          ...entry,
          ...deriveVisualMeta(entry),
          slug,
          sectionId,
          sectionTitle: sec.title,
          categoryTitle: cat.title,
          categorySlug: cat.slug,
          categoryEmoji: cat.emoji,
          addedAt: entry.addedAt ?? null,
          isNew: false,
          searchText,
        });
      }
    }

    sections.push({
      id: sectionId,
      emoji: sec.emoji,
      title: sec.title,
      categories: secCategories,
      itemCount: secItemCount,
    });
  }

  // Deterministic "New" window (14 days from latest catalog addition) to avoid SSR hydration mismatches
  let latestAddedDate: string | null = null;
  for (const item of items) {
    if (item.addedAt && (!latestAddedDate || item.addedAt > latestAddedDate)) {
      latestAddedDate = item.addedAt;
    }
  }
  const latestMs = latestAddedDate ? Date.parse(`${latestAddedDate}T00:00:00Z`) : 0;
  const NEW_WINDOW_MS = 14 * 86_400_000;
  if (latestMs > 0) {
    for (const item of items) {
      if (item.addedAt) {
        const itemMs = Date.parse(`${item.addedAt}T00:00:00Z`);
        if (!Number.isNaN(itemMs) && latestMs - itemMs <= NEW_WINDOW_MS) {
          item.isNew = true;
        }
      }
    }
  }

  return {
    sections,
    categories,
    items,
    totalCount: items.length,
    latestAddedDate,
    newCount: items.filter((i) => i.isNew).length,
    extensionsCount: items.filter(
      (i) => i.platforms.includes("extensions") || Boolean(i.blenderExtensionId)
    ).length,
    openSourceCount: items.filter(
      (i) =>
        i.platforms.includes("open-source") ||
        i.platforms.includes("github") ||
        i.licenses.includes("gpl") ||
        i.licenses.includes("mit")
    ).length,
    freeCount: items.filter((i) => i.isFree).length,
  };
}

export const DIRECTORY_DATA = buildDirectoryData();

export type {
  CatalogCategory,
  CatalogSubgroup,
  LicenseCode,
  Locale,
  LocalizedText,
  PlatformTag,
};
