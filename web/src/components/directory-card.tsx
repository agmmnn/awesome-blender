import * as React from "react";
import { ArrowUpRight, Blocks, Bookmark } from "lucide-react";
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

interface DirectoryCardProps {
  item: DirectoryItem;
  lang: Locale;
  isStarred: boolean;
  onToggleStar: (id: string) => void;
  onOpenDetail: (item: DirectoryItem) => void;
  onSelectCategory?: (
    sectionId: DirectoryItem["sectionId"],
    categorySlug: string,
    subgroupId?: string | null
  ) => void;
}

export function DirectoryCard({
  item,
  lang,
  isStarred,
  onToggleStar,
  onOpenDetail,
  onSelectCategory,
}: DirectoryCardProps) {
  const title = item.title[lang] || item.title.en;
  const description = item.description[lang] || item.description.en;
  const categoryName = item.categoryTitle[lang] || item.categoryTitle.en;
  const subgroupName = item.subgroup
    ? item.subgroup[lang] || item.subgroup.en
    : null;
  const fullCategoryLabel = subgroupName
    ? `${categoryName} · ${subgroupName}`
    : categoryName;

  const githubUrl = item.githubRepo
    ? `https://github.com/${item.githubRepo}`
    : null;
  const extensionLink =
    item.secondaryLinks.find((l) => l.url.includes("extensions.blender.org"))
      ?.url ??
    (item.url?.includes("extensions.blender.org") ? item.url : null);

  return (
    <Card
      as="article"
      onClick={() => onOpenDetail(item)}
      className="directory-card group h-full cursor-pointer"
    >
      <CardHeader>
        <CardTitle as="h2" className="text-[15px]">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onOpenDetail(item);
            }}
            className="block w-full truncate text-left font-semibold text-foreground group-hover:text-primary transition-colors cursor-pointer"
          >
            {title}
          </button>
        </CardTitle>

        {/* Fixed 4-slot action bar so icon positions remain aligned across all cards */}
        <CardAction onClick={(e) => e.stopPropagation()}>
          {/* Slot 1: Blender Extensions Platform */}
          <Tooltip>
            <TooltipTrigger asChild>
              {extensionLink ? (
                <Button
                  asChild
                  variant="ghost"
                  size="icon-sm"
                  className="text-foreground/75 hover:text-foreground"
                >
                  <a
                    href={extensionLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={
                      lang === "zh"
                        ? "在 Blender 官方扩展平台打开"
                        : "Open on Blender Extensions Platform"
                    }
                  >
                    <Blocks className="size-3.5" />
                  </a>
                </Button>
              ) : (
                <span
                  aria-label={
                    lang === "zh"
                      ? "未在 Blender 扩展平台上架"
                      : "Not on Blender Extensions Platform"
                  }
                  className="inline-flex size-7 items-center justify-center rounded-md text-muted-foreground/25 select-none"
                >
                  <Blocks className="size-3.5" />
                </span>
              )}
            </TooltipTrigger>
            <TooltipContent>
              {extensionLink
                ? lang === "zh"
                  ? "Blender 官方扩展平台 (Extensions)"
                  : "Official Blender Extensions Platform"
                : lang === "zh"
                  ? "未在官方扩展平台列出"
                  : "Not listed on Blender Extensions"}
            </TooltipContent>
          </Tooltip>

          {/* Slot 2: GitHub Repository */}
          <Tooltip>
            <TooltipTrigger asChild>
              {githubUrl ? (
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
              ) : (
                <span
                  aria-label={
                    lang === "zh" ? "无公开 GitHub 仓库" : "No GitHub repository"
                  }
                  className="inline-flex size-7 items-center justify-center rounded-md text-muted-foreground/25 select-none"
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    className="size-3.5"
                    aria-hidden="true"
                  >
                    <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
                  </svg>
                </span>
              )}
            </TooltipTrigger>
            <TooltipContent>
              {githubUrl
                ? `GitHub: ${item.githubRepo}`
                : lang === "zh"
                  ? "无 GitHub 仓库链接"
                  : "No GitHub repository"}
            </TooltipContent>
          </Tooltip>

          {/* Slot 3: Bookmark / Save */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                onClick={() => onToggleStar(item.id)}
                aria-pressed={isStarred}
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

          {/* Slot 4: Direct External Link (distinct from card detail click) */}
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
              {lang === "zh"
                ? "直接访问网站 / 下载 (↗)"
                : "Open website / download directly (↗)"}
            </TooltipContent>
          </Tooltip>
        </CardAction>
      </CardHeader>

      {/* Description (clicking anywhere on card opens full detail modal) */}
      <CardContent>
        <CardDescription className="line-clamp-2">
          {description}
        </CardDescription>
      </CardContent>

      {/* Two-row Footer: Row 1 = Truncated Category Tag, Row 2 = Explained Badges */}
      <CardFooter>
        {/* Row 1: Category & Subgroup Pill (strictly truncated to 1 line) */}
        <div className="w-full min-w-0">
          <Badge
            variant="secondary"
            className="max-w-full min-w-0 justify-start px-2 py-0.5 text-[11px] font-medium"
          >
            <span className="truncate block max-w-full">
              {fullCategoryLabel}
            </span>
          </Badge>
        </div>

        {/* Row 2: Metadata Badges on a separate line so they never overlap */}
        <div className="flex items-center justify-between gap-1.5 flex-wrap w-full">
          <div className="flex items-center gap-1.5 flex-wrap">
            {extensionLink && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge
                    variant="outline"
                    className="text-[11px] px-1.5 py-0 font-normal text-foreground/85 cursor-help"
                  >
                    Extension
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  {lang === "zh"
                    ? "Blender 4.2+ 官方扩展平台插件（支持一键拖拽安装与更新）"
                    : "Official Blender 4.2+ Extension — install directly from extensions.blender.org"}
                </TooltipContent>
              </Tooltip>
            )}

            {item.licenses.map((lic) => {
              const info = LICENSE_INFO[lic];
              return (
                <Tooltip key={lic}>
                  <TooltipTrigger asChild>
                    <Badge
                      variant="outline"
                      className="text-[11px] px-1.5 py-0 font-normal text-foreground/85 cursor-help"
                    >
                      {info ? info.label : lic.toUpperCase()}
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>
                    {info
                      ? lang === "zh"
                        ? info.tooltipZh
                        : info.tooltipEn
                      : lic.toUpperCase()}
                  </TooltipContent>
                </Tooltip>
              );
            })}
          </div>

          <Tooltip>
            <TooltipTrigger asChild>
              <Badge
                variant={item.isPaid ? "default" : "outline"}
                className={cn(
                  "text-[11px] px-1.5 py-0 cursor-help ml-auto",
                  !item.isPaid && "text-foreground/75 font-normal"
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
            </TooltipTrigger>
            <TooltipContent>
              {item.isPaid
                ? lang === "zh"
                  ? "商业付费产品"
                  : "Paid / Commercial product"
                : lang === "zh"
                  ? "免费下载与使用"
                  : "Free to download and use"}
            </TooltipContent>
          </Tooltip>
        </div>
      </CardFooter>
    </Card>
  );
}
