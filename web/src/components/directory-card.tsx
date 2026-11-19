import * as React from "react";
import { ArrowUpRight, Blocks, Bookmark, Star } from "lucide-react";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { DirectoryItem, Locale } from "@/lib/catalog";
import { cn } from "@/lib/utils";

export function formatCompactStars(stars: number): string {
  if (stars >= 1000) {
    const k = stars / 1000;
    return `${k >= 10 ? k.toFixed(1).replace(/\.0$/, "") : k.toFixed(1).replace(/\.0$/, "")}k`;
  }
  return String(stars);
}

const EN_MONTHS = [
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
];

export interface UpdatedDateInfo {
  shortLabel: string;
  monthYear: string;
  relativeLabel: string;
  isStale: boolean;
}

export function formatUpdatedInfo(
  isoDate: string | null,
  lang: Locale
): UpdatedDateInfo | null {
  if (!isoDate) return null;
  const parts = isoDate.split("-").map(Number);
  if (parts.length < 2 || Number.isNaN(parts[0]) || Number.isNaN(parts[1])) {
    return null;
  }
  const [year, month, day = 1] = parts;
  const dateMs = Date.UTC(year, month - 1, day);
  const nowMs = Date.now();
  const diffDays = Math.max(0, Math.floor((nowMs - dateMs) / 86_400_000));
  const diffMonths = Math.floor(diffDays / 30.44);
  const diffYears = Math.floor(diffDays / 365.25);

  const monthName = EN_MONTHS[month - 1] ?? String(month);
  const monthYear =
    lang === "zh" ? `${year}年${month}月` : `${monthName} ${year}`;

  let relativeLabel: string;
  if (diffDays < 7) {
    relativeLabel = lang === "zh" ? "本周" : "this week";
  } else if (diffDays < 31) {
    const weeks = Math.max(1, Math.floor(diffDays / 7));
    relativeLabel = lang === "zh" ? `${weeks}周前` : `${weeks}w ago`;
  } else if (diffMonths < 12) {
    const m = Math.max(1, diffMonths);
    relativeLabel = lang === "zh" ? `${m}个月前` : `${m}mo ago`;
  } else {
    const y = Math.max(1, diffYears);
    relativeLabel = lang === "zh" ? `${y}年前` : `${y}y ago`;
  }

  // Show relative time ("2mo ago", "3w ago") when updated within the past year,
  // and readable Month Year ("Mar 2024") when older than a year
  const shortLabel = diffMonths < 12 ? relativeLabel : monthYear;
  const isStale = diffDays > 540; // > ~18 months without commits

  return {
    shortLabel,
    monthYear,
    relativeLabel,
    isStale,
  };
}

export function formatAddedDate(
  isoDate: string | null,
  lang: Locale
): string | null {
  if (!isoDate) return null;
  const parts = isoDate.split("-").map(Number);
  if (parts.length < 3 || parts.some(Number.isNaN)) return isoDate;
  const [year, month, day] = parts;
  const monthName = EN_MONTHS[month - 1] ?? String(month);
  return lang === "zh"
    ? `${year}年${month}月${day}日`
    : `${monthName} ${day}, ${year}`;
}

const LICENSE_INFO: Record<
  string,
  { label: string; tooltipEn: string; tooltipZh: string }
> = {
  gpl: {
    label: "GPL",
    tooltipEn: "GNU General Public License — Free & Open Source",
    tooltipZh: "GNU 通用公共许可证 — 免费且开源",
  },
  mit: {
    label: "MIT",
    tooltipEn: "MIT License — Permissive Free & Open Source",
    tooltipZh: "MIT 许可证 — 宽松免费开源",
  },
  zero: {
    label: "CC0",
    tooltipEn: "Creative Commons Zero — Public Domain (No Attribution Required)",
    tooltipZh: "CC0 公共领域 — 可免费用于任何商业或个人用途",
  },
  cc: {
    label: "CC",
    tooltipEn: "Creative Commons License",
    tooltipZh: "知识共享 (Creative Commons) 许可证",
  },
  by: {
    label: "CC-BY",
    tooltipEn: "Creative Commons Attribution — Free to use with credit",
    tooltipZh: "CC-BY 署名许可 — 署名即可免费使用",
  },
  nc: {
    label: "CC-NC",
    tooltipEn: "Creative Commons Non-Commercial",
    tooltipZh: "CC-NC 非商业性使用许可",
  },
};

const MEDIA_TYPE_INFO: Record<
  NonNullable<DirectoryItem["mediaType"]>,
  { labelEn: string; labelZh: string }
> = {
  video: { labelEn: "▷ Video", labelZh: "▷ 视频" },
  playlist: { labelEn: "☰ Playlist", labelZh: "☰ 播放列表" },
  channel: { labelEn: "☷ Channel", labelZh: "☷ 频道" },
  doc: { labelEn: "🧾 Docs", labelZh: "🧾 文档" },
  course: { labelEn: "📦 Course", labelZh: "📦 课程" },
};

interface DirectoryCardProps {
  item: DirectoryItem;
  lang: Locale;
  isStarred: boolean;
  activeCategory?: string;
  onToggleStar: (id: string) => void;
  onOpenDetail: (item: DirectoryItem) => void;
  onSelectCategory?: (
    sectionId: DirectoryItem["sectionId"],
    categorySlug: string,
    subgroupId?: string | null
  ) => void;
}

export const DirectoryCard = React.memo(function DirectoryCard({
  item,
  lang,
  isStarred,
  activeCategory,
  onToggleStar,
  onOpenDetail,
  onSelectCategory,
}: DirectoryCardProps) {
  const [avatarError, setAvatarError] = React.useState(false);
  const [previewError, setPreviewError] = React.useState(false);

  const title = item.title[lang] || item.title.en;
  const description = item.description[lang] || item.description.en;
  const categoryName = item.categoryTitle[lang] || item.categoryTitle.en;
  const subgroupName = item.subgroup
    ? item.subgroup[lang] || item.subgroup.en
    : null;
  const isCategoryAlreadyActive =
    Boolean(activeCategory) &&
    activeCategory !== "all" &&
    activeCategory === item.categorySlug;

  const fullCategoryLabel = subgroupName
    ? `${categoryName} · ${subgroupName}`
    : categoryName;

  const displayCategoryLabel =
    isCategoryAlreadyActive && subgroupName
      ? subgroupName
      : item.categoryEmoji
        ? `${item.categoryEmoji} ${fullCategoryLabel}`
        : fullCategoryLabel;

  const githubUrl = item.githubRepo
    ? `https://github.com/${item.githubRepo}`
    : null;
  const extensionLink =
    item.secondaryLinks.find((l) => l.url.includes("extensions.blender.org"))
      ?.url ??
    (item.url?.includes("extensions.blender.org") ? item.url : null);
  const mediaInfo = item.mediaType ? MEDIA_TYPE_INFO[item.mediaType] : null;
  const showAvatar = Boolean(item.avatarUrl) && !avatarError;
  const showPreview = Boolean(item.previewImageUrl) && !previewError;
  const updatedInfo = formatUpdatedInfo(item.githubPushedAt, lang);

  return (
    <Card
      as="article"
      role="button"
      tabIndex={0}
      onClick={() => onOpenDetail(item)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpenDetail(item);
        }
      }}
      className="directory-card group h-full cursor-pointer"
    >
      <CardHeader>
        <div className="flex items-center gap-3 min-w-0">
          {/* App Avatar / Favicon */}
          <div className="relative size-9 shrink-0 rounded-lg border border-border/80 bg-muted/45 flex items-center justify-center shadow-2xs">
            {showAvatar ? (
              <img
                src={item.avatarUrl!}
                alt=""
                width={24}
                height={24}
                loading="lazy"
                decoding="async"
                onError={() => setAvatarError(true)}
                className="size-6 rounded-sm object-contain"
              />
            ) : (
              <span className="text-base leading-none select-none">
                {item.categoryEmoji || "📦"}
              </span>
            )}
          </div>

          <div className="min-w-0 flex-1">
            <CardTitle as="h2" className="text-[15px] leading-snug">
              <span className="block truncate font-semibold text-foreground group-hover:text-primary transition-colors">
                {title}
              </span>
            </CardTitle>
            {item.domainLabel && (
              <p className="truncate text-[11px] text-muted-foreground mt-0.5">
                {item.domainLabel}
              </p>
            )}
          </div>
        </div>

        {/* Action bar: Blender Extensions + GitHub + Bookmark + Direct External Link */}
        <CardAction onClick={(e) => e.stopPropagation()}>
          {/* Blender Extensions Platform (rendered only when available) */}
          {extensionLink && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  asChild
                  variant="ghost"
                  size="icon-sm"
                  className="text-orange-500/85 hover:text-orange-500"
                >
                  <a
                    href={extensionLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={
                      lang === "zh"
                        ? "Blender 官方扩展平台 (extensions.blender.org)"
                        : "Official Blender Extension (extensions.blender.org)"
                    }
                    aria-label={
                      lang === "zh"
                        ? "在 Blender 官方扩展平台打开"
                        : "Open on Blender Extensions Platform"
                    }
                  >
                    <Blocks className="size-3.5" />
                  </a>
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {lang === "zh"
                  ? "Blender 官方扩展平台 (extensions.blender.org)"
                  : "Official Blender Extension (extensions.blender.org)"}
              </TooltipContent>
            </Tooltip>
          )}

          {/* GitHub Repository (rendered only when available) */}
          {githubUrl && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  asChild
                  variant="ghost"
                  size="icon-sm"
                  className="text-foreground/75 hover:text-foreground"
                >
                  <a
                    href={githubUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={`GitHub: ${item.githubRepo}`}
                    aria-label={`GitHub repository: ${item.githubRepo}`}
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="currentColor"
                      className="size-3.5"
                      aria-hidden="true"
                    >
                      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
                    </svg>
                  </a>
                </Button>
              </TooltipTrigger>
              <TooltipContent>{`GitHub: ${item.githubRepo}`}</TooltipContent>
            </Tooltip>
          )}

          {/* Bookmark / Save */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                onClick={() => onToggleStar(item.id)}
                aria-pressed={isStarred}
                title={
                  isStarred
                    ? lang === "zh"
                      ? "已收藏（点击移除）"
                      : "Saved in Stack (click to remove)"
                    : lang === "zh"
                      ? "保存到收藏夹"
                      : "Save to Stack"
                }
                aria-label={
                  isStarred
                    ? lang === "zh"
                      ? "取消收藏"
                      : "Remove from Saved"
                    : lang === "zh"
                      ? "加入收藏夹"
                      : "Save to Stack"
                }
                className={cn(
                  "text-foreground/75 hover:text-foreground",
                  isStarred && "text-foreground"
                )}
              >
                <Bookmark
                  className={cn("size-3.5", isStarred && "fill-current")}
                />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              {isStarred
                ? lang === "zh"
                  ? "已收藏（点击移除）"
                  : "Saved in Stack (click to remove)"
                : lang === "zh"
                  ? "保存到收藏夹"
                  : "Save to Stack"}
            </TooltipContent>
          </Tooltip>

          {/* Direct External Link (distinct from card detail click) */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                asChild
                variant="ghost"
                size="icon-sm"
                className="text-foreground/75 hover:text-foreground"
              >
                <a
                  href={item.url ?? "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={
                    lang === "zh"
                      ? `直接访问 ${title} (↗)`
                      : `Open ${title} website directly (↗)`
                  }
                  aria-label={
                    lang === "zh"
                      ? `在新标签页打开 ${title}`
                      : `Open ${title} website in new tab`
                  }
                >
                  <ArrowUpRight className="size-4" />
                </a>
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              {lang === "zh" ? "访问网站 (↗)" : "Open website (↗)"}
            </TooltipContent>
          </Tooltip>
        </CardAction>
      </CardHeader>

      {/* Optional Thumbnail Preview + Description */}
      <CardContent className="space-y-2.5">
        {showPreview && (
          <div className="relative h-32 w-full overflow-hidden rounded-lg border border-border/60 bg-muted/35">
            <img
              src={item.previewImageUrl!}
              alt={title}
              loading="lazy"
              decoding="async"
              onError={() => setPreviewError(true)}
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
            />
          </div>
        )}
        <CardDescription className="line-clamp-3 text-[13px] leading-relaxed">
          {description}
        </CardDescription>
      </CardContent>

      {/* Two-row Footer: Row 1 = Clickable Category Tag, Row 2 = Trust & Metadata Badges */}
      <CardFooter>
        {/* Row 1: Interactive Category & Subgroup Pill */}
        <div className="w-full min-w-0">
          <Badge
            asChild={Boolean(onSelectCategory)}
            variant="secondary"
            className={cn(
              "max-w-full min-w-0 justify-start px-2 py-0.5 text-[11px] font-medium",
              onSelectCategory &&
                "hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer"
            )}
          >
            {onSelectCategory ? (
              <button
                type="button"
                title={fullCategoryLabel}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectCategory(
                    item.sectionId,
                    item.categorySlug,
                    item.subgroupId
                  );
                }}
              >
                <span className="truncate block max-w-full">
                  {displayCategoryLabel}
                </span>
              </button>
            ) : (
              <span className="truncate block max-w-full">
                {displayCategoryLabel}
              </span>
            )}
          </Badge>
        </div>

        {/* Row 2: Metadata & Trust Badges */}
        <div className="flex items-center justify-between gap-1.5 flex-wrap w-full">
          <div className="flex items-center gap-1.5 flex-wrap">
            {item.isNew && (
              <Badge
                variant="outline"
                title={
                  item.addedAt
                    ? lang === "zh"
                      ? `收录于 ${formatAddedDate(item.addedAt, lang)}`
                      : `Added to directory on ${formatAddedDate(item.addedAt, lang)}`
                    : undefined
                }
                className="text-[11px] px-1.5 py-0 font-medium border-violet-500/35 bg-violet-500/10 text-violet-600 dark:text-violet-400 cursor-help"
              >
                {lang === "zh" ? "✨ 新增" : "✨ New"}
              </Badge>
            )}

            {mediaInfo && (
              <Badge
                variant="outline"
                className="text-[11px] px-1.5 py-0 font-normal border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400"
              >
                {lang === "zh" ? mediaInfo.labelZh : mediaInfo.labelEn}
              </Badge>
            )}

            {item.licenses.map((lic) => {
              const info = LICENSE_INFO[lic];
              return (
                <Badge
                  key={lic}
                  variant="outline"
                  title={
                    info
                      ? lang === "zh"
                        ? info.tooltipZh
                        : info.tooltipEn
                      : lic.toUpperCase()
                  }
                  className="text-[11px] px-1.5 py-0 font-medium border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 cursor-help"
                >
                  {info ? info.label : lic.toUpperCase()}
                </Badge>
              );
            })}

            {/* GitHub Stars & Last Updated Trust Signal */}
            {item.githubStars !== null && githubUrl && (
              <Badge
                asChild
                variant="outline"
                className="text-[11px] px-1.5 py-0 font-normal text-foreground/80 hover:bg-accent transition-colors cursor-pointer gap-1"
              >
                <a
                  href={githubUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  title={
                    lang === "zh"
                      ? `GitHub: ${item.githubStars.toLocaleString()} 星${
                          updatedInfo
                            ? ` · 最近更新：${updatedInfo.monthYear} (${updatedInfo.relativeLabel}${updatedInfo.isStale ? "，较久未更新" : ""})`
                            : ""
                        }`
                      : `${item.githubStars.toLocaleString()} GitHub stars${
                          updatedInfo
                            ? ` · Last updated ${updatedInfo.monthYear} (${updatedInfo.relativeLabel}${updatedInfo.isStale ? " — inactive for 18+ months" : ""})`
                            : ""
                        }`
                  }
                >
                  <Star className="size-2.5 fill-amber-400 text-amber-400 shrink-0" />
                  <span>{formatCompactStars(item.githubStars)}</span>
                  {updatedInfo && (
                    <span
                      className={cn(
                        "text-muted-foreground",
                        updatedInfo.isStale && "opacity-50"
                      )}
                    >
                      · {updatedInfo.shortLabel}
                    </span>
                  )}
                </a>
              </Badge>
            )}
          </div>

          <Badge
            variant="outline"
            title={
              item.isPaid
                ? lang === "zh"
                  ? "商业付费产品"
                  : "Paid / Commercial product"
                : lang === "zh"
                  ? "免费使用"
                  : "Free to use"
            }
            className={cn(
              "text-[11px] px-1.5 py-0 cursor-help ml-auto font-normal",
              item.isPaid
                ? "border-amber-500/35 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                : "text-foreground/75"
            )}
          >
            {item.isPaid
              ? lang === "zh"
                ? "付费"
                : "Paid"
              : lang === "zh"
                ? "免费"
                : "Free"}
          </Badge>
        </div>
      </CardFooter>
    </Card>
  );
});
