import rawCatalogJson from "@/data/catalog.json";
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

const rawCatalog = rawCatalogJson as unknown as CatalogData;

export type DirectorySectionId = "add-ons" | "resources" | "standalone";

const ALLOWED_SECTIONS = new Set<string>([
  "add-ons",
  "resources",
  "standalone",
]);

/**
 * Exclude non-downloadable reference/article categories inside Resources
 * so every item in the directory is a downloadable/usable add-on, asset, or tool.
 */
const EXCLUDED_CATEGORY_IDS = new Set<string>([
  "resources/art-reference",
  "resources/useful",
  "resources/free-stocks",
]);

export interface DirectoryItem extends CatalogEntry {
  sectionId: DirectorySectionId;
  sectionTitle: LocalizedText;
  categoryTitle: LocalizedText;
  categorySlug: string;
  searchText: string;
}

export interface DirectoryCategory {
  id: string;
  slug: string;
  sectionId: DirectorySectionId;
  title: LocalizedText;
  subgroups: CatalogSubgroup[];
  itemCount: number;
}

export interface DirectorySection {
  id: DirectorySectionId;
  title: LocalizedText;
  categories: DirectoryCategory[];
  itemCount: number;
}

function buildDirectoryData() {
  const sections: DirectorySection[] = [];
  const categories: DirectoryCategory[] = [];
  const items: DirectoryItem[] = [];

  for (const sec of rawCatalog.sections) {
    if (!ALLOWED_SECTIONS.has(sec.id)) continue;
    const sectionId = sec.id as DirectorySectionId;
    const secCategories: DirectoryCategory[] = [];
    let secItemCount = 0;

    for (const cat of sec.categories) {
      if (EXCLUDED_CATEGORY_IDS.has(cat.id)) continue;

      const validEntries = cat.entries.filter(
        (e) => e.kind === "item" && Boolean(e.url)
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
        title: cat.title,
        subgroups: validSubgroups,
        itemCount: validEntries.length,
      };

      secCategories.push(dirCat);
      categories.push(dirCat);
      secItemCount += validEntries.length;

      for (const entry of validEntries) {
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
          sectionId,
          sectionTitle: sec.title,
          categoryTitle: cat.title,
          categorySlug: cat.slug,
          searchText,
        });
      }
    }

    sections.push({
      id: sectionId,
      title: sec.title,
      categories: secCategories,
      itemCount: secItemCount,
    });
  }

  return {
    sections,
    categories,
    items,
    totalCount: items.length,
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
