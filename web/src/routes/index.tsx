import * as React from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Bookmark,
  RotateCcw,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import {
  DIRECTORY_DATA,
  type DirectoryItem,
  type DirectorySectionId,
  type Locale,
} from "@/lib/catalog";
import { buildDirectorySeo, filterDirectoryItems } from "@/lib/seo";
import { DirectoryCard } from "@/components/directory-card";
import { ItemDetailDialog } from "@/components/item-detail-dialog";
import { ScrollablePillBar } from "@/components/scrollable-pill-bar";
import { StackDialog } from "@/components/stack-dialog";
import { ThemeToggle } from "@/components/theme-toggle";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export interface DirectorySearchParams {
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
  lang?: Locale;
}

export const Route = createFileRoute("/")({
  validateSearch: (search: Record<string, unknown>): DirectorySearchParams => {
    const section =
      search.section === "add-ons" ||
      search.section === "resources" ||
      search.section === "standalone"
        ? search.section
        : undefined;
    const category =
      typeof search.category === "string" && search.category
        ? search.category
        : undefined;
    const subgroup =
      typeof search.subgroup === "string" && search.subgroup
        ? search.subgroup
        : undefined;
    const q =
      typeof search.q === "string" && search.q.trim()
        ? search.q.trim()
        : undefined;
    const price =
      search.price === "free" || search.price === "paid"
        ? search.price
        : undefined;
    const platform =
      search.platform === "extensions" ||
      search.platform === "github" ||
      search.platform === "open-source" ||
      search.platform === "superhive" ||
      search.platform === "gumroad"
        ? search.platform
        : undefined;
    const license =
      search.license === "gpl" ||
      search.license === "mit" ||
      search.license === "zero" ||
      search.license === "cc"
        ? search.license
        : undefined;
    const lang = search.lang === "zh" ? "zh" : undefined;

    return {
      section,
      category,
      subgroup,
      q,
      price,
      platform,
      license,
      lang,
    };
  },
  head: ({ match }) => {
    const seo = buildDirectorySeo(match.search);
    return {
      meta: [
        { title: seo.title },
        { name: "description", content: seo.description },
        { name: "robots", content: seo.robotsContent },
        { property: "og:title", content: seo.title },
        { property: "og:description", content: seo.description },
        { property: "og:url", content: seo.canonicalUrl },
        {
          property: "og:locale",
          content: seo.lang === "zh" ? "zh_CN" : "en_US",
        },
        { name: "twitter:title", content: seo.title },
        { name: "twitter:description", content: seo.description },
        { "script:ld+json": seo.jsonLd },
      ],
      links: [
        { rel: "canonical", href: seo.canonicalUrl },
        { rel: "alternate", hrefLang: "en", href: seo.enAlternateUrl },
        { rel: "alternate", hrefLang: "zh", href: seo.zhAlternateUrl },
        { rel: "alternate", hrefLang: "x-default", href: seo.enAlternateUrl },
      ],
    };
  },
  component: DirectoryPage,
});

function DirectoryPage() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();

  const activeSection = search.section ?? "all";
  const activeCategory = search.category ?? "all";
  const activeSubgroup = search.subgroup ?? "all";
  const activePrice = search.price ?? "all";
  const activePlatform = search.platform ?? "all";
  const activeLicense = search.license ?? "all";
  const lang: Locale = search.lang ?? "en";
  const query = search.q ?? "";

  const [searchInput, setSearchInput] = React.useState(query);
  const [detailItem, setDetailItem] = React.useState<DirectoryItem | null>(
    null
  );

  const searchInputRef = React.useRef<HTMLInputElement | null>(null);
  const stackDialogRef = React.useRef<HTMLDialogElement | null>(null);
  const detailDialogRef = React.useRef<HTMLDialogElement | null>(null);

  React.useEffect(() => {
    setSearchInput(query);
  }, [query]);

  // Saved / bookmarked items in localStorage
  const [starredIds, setStarredIds] = React.useState<string[]>([]);

  React.useEffect(() => {
    try {
      const raw = localStorage.getItem("awesome-blender-stack");
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) setStarredIds(parsed);
      }
    } catch {}
  }, []);

  const toggleStar = React.useCallback((id: string) => {
    setStarredIds((prev) => {
      const next = prev.includes(id)
        ? prev.filter((x) => x !== id)
        : [...prev, id];
      try {
        localStorage.setItem("awesome-blender-stack", JSON.stringify(next));
      } catch {}
      return next;
    });
  }, []);

  const clearStars = React.useCallback(() => {
    setStarredIds([]);
    try {
      localStorage.removeItem("awesome-blender-stack");
    } catch {}
  }, []);

  const starredSet = React.useMemo(() => new Set(starredIds), [starredIds]);
  const starredItems = React.useMemo(
    () => DIRECTORY_DATA.items.filter((i) => starredSet.has(i.id)),
    [starredSet]
  );

  const handleOpenDetail = React.useCallback((item: DirectoryItem) => {
    setDetailItem(item);
    requestAnimationFrame(() => {
      detailDialogRef.current?.showModal();
    });
  }, []);

  // Keyboard shortcut `/` or `Cmd/Ctrl + K` to focus search
  React.useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (
        (e.key === "/" &&
          document.activeElement !== searchInputRef.current &&
          !e.metaKey &&
          !e.ctrlKey) ||
        ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k")
      ) {
        e.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const updateSearch = React.useCallback(
    (patch: Partial<DirectorySearchParams>) => {
      navigate({
        search: (prev) => {
          const next = { ...prev, ...patch };
          return {
            section:
              next.section && next.section !== "all" ? next.section : undefined,
            category:
              next.category && next.category !== "all"
                ? next.category
                : undefined,
            subgroup:
              next.subgroup && next.subgroup !== "all"
                ? next.subgroup
                : undefined,
            q: next.q && next.q.trim() ? next.q.trim() : undefined,
            price: next.price && next.price !== "all" ? next.price : undefined,
            platform:
              next.platform && next.platform !== "all"
                ? next.platform
                : undefined,
            license:
              next.license && next.license !== "all" ? next.license : undefined,
            lang: next.lang === "zh" ? "zh" : undefined,
          };
        },
        replace: true,
      });
    },
    [navigate]
  );

  const visibleCategories = React.useMemo(() => {
    if (activeSection === "all") return DIRECTORY_DATA.categories;
    return DIRECTORY_DATA.categories.filter(
      (c) => c.sectionId === activeSection
    );
  }, [activeSection]);

  const selectedCategoryObj = React.useMemo(() => {
    if (activeCategory === "all") return null;
    return (
      visibleCategories.find((c) => c.slug === activeCategory) ??
      DIRECTORY_DATA.categories.find((c) => c.slug === activeCategory) ??
      null
    );
  }, [activeCategory, visibleCategories]);

  const filteredItems = React.useMemo(
    () =>
      filterDirectoryItems(
        {
          section: activeSection,
          category: activeCategory,
          subgroup: activeSubgroup,
          price: activePrice,
          platform: activePlatform,
          license: activeLicense,
          q: searchInput,
          lang,
        },
        searchInput
      ),
    [
      activeSection,
      activeCategory,
      activeSubgroup,
      activePrice,
      activePlatform,
      activeLicense,
      searchInput,
      lang,
    ]
  );

  const seo = React.useMemo(
    () =>
      buildDirectorySeo({
        section: activeSection,
        category: activeCategory,
        subgroup: activeSubgroup,
        price: activePrice,
        platform: activePlatform,
        license: activeLicense,
        q: searchInput,
        lang,
      }),
    [
      activeSection,
      activeCategory,
      activeSubgroup,
      activePrice,
      activePlatform,
      activeLicense,
      searchInput,
      lang,
    ]
  );

  const hasActiveFilters =
    activeSection !== "all" ||
    activeCategory !== "all" ||
    activeSubgroup !== "all" ||
    activePrice !== "all" ||
    activePlatform !== "all" ||
    activeLicense !== "all" ||
    searchInput.trim() !== "";

  const handleResetFilters = () => {
    setSearchInput("");
    updateSearch({
      section: undefined,
      category: undefined,
      subgroup: undefined,
      q: undefined,
      price: undefined,
      platform: undefined,
      license: undefined,
    });
  };

  return (
    <TooltipProvider delayDuration={150}>
      <div className="min-h-screen w-full flex flex-col items-center overflow-x-clip">
        {/* Sticky Minimal Navbar (Centered) */}
        <header className="sticky top-0 z-30 w-full border-b border-border bg-background/90 backdrop-blur-md">
          <div className="mx-auto flex h-18 sm:h-20 w-full max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
            {/* Brand */}
            <div className="flex items-center gap-3.5 min-w-0">
              <button
                type="button"
                onClick={handleResetFilters}
                aria-label="Awesome Blender Home"
                className="pressable flex items-center text-left cursor-pointer shrink-0"
              >
                <img
                  src="/logo.png"
                  alt="Awesome Blender"
                  className="h-8 sm:h-9 w-auto object-contain shrink-0 drop-shadow-[0_1px_1.5px_rgba(0,0,0,0.28)]"
                />
              </button>
              <Badge
                variant="secondary"
                className="hidden sm:inline-flex text-xs px-2.5 py-0.5 font-medium text-foreground/80"
              >
                {DIRECTORY_DATA.totalCount}{" "}
                {lang === "zh" ? "精选项目" : "curated items"}
              </Badge>
            </div>

            {/* Primary Section Tabs (Desktop) */}
            <div className="hidden md:flex items-center">
              <Tabs
                value={activeSection}
                onValueChange={(val) =>
                  updateSearch({
                    section: val as DirectorySearchParams["section"],
                    category: undefined,
                    subgroup: undefined,
                  })
                }
              >
                <TabsList>
                  <TabsTrigger value="all">
                    <span>{lang === "zh" ? "全部" : "All"}</span>
                    <span className="rounded bg-foreground/10 px-1.5 py-0.2 text-[11px] font-semibold text-foreground/85">
                      {DIRECTORY_DATA.totalCount}
                    </span>
                  </TabsTrigger>
                  {DIRECTORY_DATA.sections.map((sec) => (
                    <TabsTrigger key={sec.id} value={sec.id}>
                      <span>{sec.title[lang] || sec.title.en}</span>
                      <span className="rounded bg-foreground/10 px-1.5 py-0.2 text-[11px] font-semibold text-foreground/85">
                        {sec.itemCount}
                      </span>
                    </TabsTrigger>
                  ))}
                </TabsList>
              </Tabs>
            </div>

            {/* Right Actions */}
            <div className="flex items-center gap-2 shrink-0">
              {/* Language Switcher */}
              <div
                className="inline-flex h-8 items-center rounded-md border border-input bg-background p-0.5 text-xs"
                role="group"
                aria-label="Language"
              >
                <button
                  type="button"
                  onClick={() => updateSearch({ lang: "en" })}
                  className={`px-2 py-1 rounded-xs font-medium transition-colors cursor-pointer ${
                    lang === "en"
                      ? "bg-secondary text-secondary-foreground"
                      : "text-foreground/75 hover:text-foreground"
                  }`}
                >
                  EN
                </button>
                <button
                  type="button"
                  onClick={() => updateSearch({ lang: "zh" })}
                  className={`px-2 py-1 rounded-xs font-medium transition-colors cursor-pointer ${
                    lang === "zh"
                      ? "bg-secondary text-secondary-foreground"
                      : "text-foreground/75 hover:text-foreground"
                  }`}
                >
                  中文
                </button>
              </div>

              {/* Saved Stack Button */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => stackDialogRef.current?.showModal()}
                    className="gap-1.5"
                  >
                    <Bookmark className="size-3.5" />
                    <span className="hidden sm:inline">
                      {lang === "zh" ? "收藏夹" : "Saved"}
                    </span>
                    <Badge
                      variant="secondary"
                      className="px-1.5 py-0 text-[11px] font-semibold text-foreground"
                    >
                      {starredIds.length}
                    </Badge>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {lang === "zh"
                    ? "查看并导出已收藏的插件与资源"
                    : "View and export your bookmarked items"}
                </TooltipContent>
              </Tooltip>

              {/* GitHub Repo Link */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button asChild variant="outline" size="icon">
                    <a
                      href="https://github.com/agmmnn/awesome-blender"
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label="Awesome Blender on GitHub"
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="currentColor"
                        className="size-4"
                        aria-hidden="true"
                      >
                        <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
                      </svg>
                    </a>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {lang === "zh"
                    ? "GitHub 仓库 (agmmnn/awesome-blender)"
                    : "GitHub Repository (agmmnn/awesome-blender)"}
                </TooltipContent>
              </Tooltip>

              {/* Theme Toggle */}
              <ThemeToggle />
            </div>
          </div>
        </header>

        {/* Main Directory Container (Centered with max-w-7xl and min-w-0) */}
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8 space-y-5 min-w-0">
          {/* Semantic Directory Heading & Contextual Lead */}
          <div className="space-y-1">
            <h1 className="text-xl sm:text-2xl font-semibold tracking-tight text-foreground">
              {seo.heading}
            </h1>
            <p className="text-sm text-foreground/80 max-w-3xl">
              {seo.subtitle}
            </p>
          </div>

          {/* Mobile Section Switcher */}
          <div className="md:hidden">
            <Tabs
              value={activeSection}
              onValueChange={(val) =>
                updateSearch({
                  section: val as DirectorySearchParams["section"],
                  category: undefined,
                  subgroup: undefined,
                })
              }
            >
              <TabsList className="w-full">
                <TabsTrigger value="all">
                  {lang === "zh" ? "全部" : "All"}
                </TabsTrigger>
                {DIRECTORY_DATA.sections.map((sec) => (
                  <TabsTrigger key={sec.id} value={sec.id}>
                    {sec.title[lang] || sec.title.en}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </div>

          {/* Search & Faceted Filters Row */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between min-w-0">
            {/* Search Input */}
            <div className="relative flex-1 max-w-xl min-w-0">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                ref={searchInputRef}
                type="search"
                value={searchInput}
                onChange={(e) => {
                  const val = e.target.value;
                  setSearchInput(val);
                  updateSearch({ q: val || undefined });
                }}
                placeholder={
                  lang === "zh"
                    ? "搜索插件、3D 资产、HDRI、独立工具或 GitHub 仓库..."
                    : "Search add-ons, 3D assets, HDRIs, standalone tools, or GitHub repos..."
                }
                className="pl-9 pr-14"
                aria-label="Search directory"
              />
              {searchInput ? (
                <button
                  type="button"
                  onClick={() => {
                    setSearchInput("");
                    updateSearch({ q: undefined });
                    searchInputRef.current?.focus();
                  }}
                  aria-label="Clear search"
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  <X className="size-3.5" />
                </button>
              ) : (
                <kbd className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-medium text-foreground/80">
                  /
                </kbd>
              )}
            </div>

            {/* Facet Selects */}
            <div className="flex flex-wrap items-center gap-2">
              <Select
                value={activePrice}
                onValueChange={(val) =>
                  updateSearch({
                    price: val as DirectorySearchParams["price"],
                  })
                }
              >
                <SelectTrigger aria-label="Filter by pricing">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">
                    {lang === "zh" ? "所有价格" : "All Pricing"}
                  </SelectItem>
                  <SelectItem value="free">
                    {lang === "zh" ? "仅限免费" : "Free Only"}
                  </SelectItem>
                  <SelectItem value="paid">
                    {lang === "zh" ? "付费商业" : "Paid"}
                  </SelectItem>
                </SelectContent>
              </Select>

              <Select
                value={activePlatform}
                onValueChange={(val) =>
                  updateSearch({
                    platform: val as DirectorySearchParams["platform"],
                  })
                }
              >
                <SelectTrigger aria-label="Filter by source platform">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">
                    {lang === "zh" ? "所有平台" : "All Sources"}
                  </SelectItem>
                  <SelectItem value="extensions">
                    Blender Extensions ({DIRECTORY_DATA.extensionsCount})
                  </SelectItem>
                  <SelectItem value="github">GitHub</SelectItem>
                  <SelectItem value="open-source">
                    {lang === "zh" ? "开源项目" : "Open Source"} (
                    {DIRECTORY_DATA.openSourceCount})
                  </SelectItem>
                  <SelectItem value="superhive">Superhive</SelectItem>
                  <SelectItem value="gumroad">Gumroad</SelectItem>
                </SelectContent>
              </Select>

              <Select
                value={activeLicense}
                onValueChange={(val) =>
                  updateSearch({
                    license: val as DirectorySearchParams["license"],
                  })
                }
              >
                <SelectTrigger aria-label="Filter by license">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">
                    {lang === "zh" ? "所有协议" : "All Licenses"}
                  </SelectItem>
                  <SelectItem value="gpl">GPL</SelectItem>
                  <SelectItem value="mit">MIT</SelectItem>
                  <SelectItem value="zero">CC0 (Public Domain)</SelectItem>
                  <SelectItem value="cc">CC / CC-BY</SelectItem>
                </SelectContent>
              </Select>

              {hasActiveFilters && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleResetFilters}
                  className="text-foreground/80 hover:text-foreground h-9 px-2.5"
                >
                  <RotateCcw className="size-3.5" />
                  {lang === "zh" ? "重置" : "Reset"}
                </Button>
              )}
            </div>
          </div>

          {/* Scrollable Category Pills Bar (with hidden scrollbar, fade edges, and arrow buttons) */}
          <div className="space-y-2 min-w-0 w-full">
            <ScrollablePillBar ariaLabel="Categories">
              <Button
                type="button"
                variant={activeCategory === "all" ? "default" : "outline"}
                size="xs"
                onClick={() =>
                  updateSearch({ category: undefined, subgroup: undefined })
                }
                className="rounded-full shrink-0"
              >
                {lang === "zh" ? "全部类别" : "All Categories"}
              </Button>

              {visibleCategories.map((cat) => {
                const isSelected = activeCategory === cat.slug;
                return (
                  <Button
                    key={cat.id}
                    type="button"
                    variant={isSelected ? "default" : "outline"}
                    size="xs"
                    onClick={() =>
                      updateSearch({
                        category: isSelected ? undefined : cat.slug,
                        subgroup: undefined,
                      })
                    }
                    className="rounded-full shrink-0"
                  >
                    <span>{cat.title[lang] || cat.title.en}</span>
                    <span
                      className={`text-[11px] font-semibold ${
                        isSelected
                          ? "text-primary-foreground/85"
                          : "text-foreground/75"
                      }`}
                    >
                      {cat.itemCount}
                    </span>
                  </Button>
                );
              })}
            </ScrollablePillBar>

            {/* Subgroup Pills Bar (shown when a category with subgroups is active) */}
            {selectedCategoryObj && selectedCategoryObj.subgroups.length > 0 && (
              <ScrollablePillBar ariaLabel="Subcategories" className="pt-0.5">
                <span className="inline-flex items-center gap-1 text-xs font-medium text-foreground/80 pr-1 shrink-0">
                  <SlidersHorizontal className="size-3" />
                  {selectedCategoryObj.title[lang] ||
                    selectedCategoryObj.title.en}
                  :
                </span>

                <Button
                  type="button"
                  variant={activeSubgroup === "all" ? "secondary" : "ghost"}
                  size="xs"
                  onClick={() => updateSearch({ subgroup: undefined })}
                  className="h-6 px-2.5 text-xs rounded-md shrink-0"
                >
                  {lang === "zh" ? "全部" : "All"}
                </Button>

                {selectedCategoryObj.subgroups.map((sg) => {
                  const isSelected = activeSubgroup === sg.id;
                  return (
                    <Button
                      key={sg.id}
                      type="button"
                      variant={isSelected ? "secondary" : "ghost"}
                      size="xs"
                      onClick={() =>
                        updateSearch({
                          subgroup: isSelected ? undefined : sg.id,
                        })
                      }
                      className="h-6 px-2.5 text-xs rounded-md shrink-0"
                    >
                      {sg.title[lang] || sg.title.en}
                    </Button>
                  );
                })}
              </ScrollablePillBar>
            )}
          </div>

          {/* High-Contrast Status Line */}
          <div className="flex items-center justify-between text-xs text-foreground/80">
            <span>
              {lang === "zh" ? (
                <>
                  显示{" "}
                  <strong className="font-semibold text-foreground">
                    {filteredItems.length}
                  </strong>{" "}
                  个可下载工具与资源（点击卡片查看详情，点击 ↗ 直接访问）
                </>
              ) : (
                <>
                  Showing{" "}
                  <strong className="font-semibold text-foreground">
                    {filteredItems.length}
                  </strong>{" "}
                  downloadable tools &amp; resources{" "}
                  <span className="hidden sm:inline text-muted-foreground">
                    · Click any card for details or ↗ to open site
                  </span>
                </>
              )}
            </span>

            {selectedCategoryObj && (
              <span className="font-medium text-foreground truncate">
                {selectedCategoryObj.title[lang] ||
                  selectedCategoryObj.title.en}
              </span>
            )}
          </div>

          {/* Uniform Responsive Card Grid */}
          {filteredItems.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {filteredItems.map((item) => (
                <DirectoryCard
                  key={item.id}
                  item={item}
                  lang={lang}
                  isStarred={starredSet.has(item.id)}
                  onToggleStar={toggleStar}
                  onOpenDetail={handleOpenDetail}
                  onSelectCategory={(secId, catSlug, subId) =>
                    updateSearch({
                      section: secId,
                      category: catSlug,
                      subgroup: subId ?? undefined,
                    })
                  }
                />
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-20 text-center">
              <p className="text-sm font-medium text-foreground">
                {lang === "zh"
                  ? "未找到匹配的插件或资源"
                  : "No matching items found"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground max-w-sm">
                {lang === "zh"
                  ? "尝试清除筛选条件或使用其他关键词搜索。"
                  : "Try adjusting your filters or searching with a broader keyword."}
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleResetFilters}
                className="mt-4"
              >
                <RotateCcw className="size-3.5" />
                {lang === "zh" ? "重置所有筛选" : "Reset filters"}
              </Button>
            </div>
          )}
        </main>

        {/* Minimal Footer (Centered) */}
        <footer className="w-full border-t border-border py-6 text-xs text-foreground/75">
          <div className="mx-auto flex w-full max-w-7xl flex-col items-center justify-between gap-2 px-4 sm:flex-row sm:px-6 lg:px-8">
            <p>
              Awesome Blender Directory —{" "}
              {lang === "zh"
                ? "仅收录可下载、可直接使用的插件、资产与独立工具"
                : "Curated downloadable add-ons, 3D assets, and standalone tools."}
            </p>
            <div className="flex items-center gap-4">
              <a
                href="https://github.com/agmmnn/awesome-blender"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-foreground underline-offset-4 hover:underline"
              >
                GitHub
              </a>
              <a
                href="https://extensions.blender.org"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-foreground underline-offset-4 hover:underline"
              >
                Blender Extensions
              </a>
            </div>
          </div>
        </footer>

        {/* Native Modal Dialog for Saved Stack */}
        <StackDialog
          dialogRef={stackDialogRef}
          items={starredItems}
          lang={lang}
          onRemoveItem={toggleStar}
          onClearAll={clearStars}
        />

        {/* Native Modal Dialog for Card Item Detail */}
        <ItemDetailDialog
          dialogRef={detailDialogRef}
          item={detailItem}
          lang={lang}
          isStarred={detailItem ? starredSet.has(detailItem.id) : false}
          onToggleStar={toggleStar}
          onSelectCategory={(secId, catSlug, subId) =>
            updateSearch({
              section: secId,
              category: catSlug,
              subgroup: subId ?? undefined,
            })
          }
        />
      </div>
    </TooltipProvider>
  );
}
