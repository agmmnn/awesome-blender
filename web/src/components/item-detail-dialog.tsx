import * as React from "react";
import {
  ArrowUpRight,
  Blocks,
  Bookmark,
  ExternalLink,
  FolderOpen,
  Scale,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { DirectoryItem, Locale } from "@/lib/catalog";
import { cn } from "@/lib/utils";

const LICENSE_DESCRIPTIONS: Record<string, { en: string; zh: string }> = {
  gpl: {
    en: "GPL — GNU General Public License (Free & Open Source)",
    zh: "GPL — GNU 通用公共许可证（免费开源）",
  },
  mit: {
    en: "MIT — Permissive Open Source License",
    zh: "MIT — 宽松开源许可证",
  },
  zero: {
    en: "CC0 — Creative Commons Zero (Public Domain)",
    zh: "CC0 — 知识共享零（公共领域）",
  },
  cc: {
    en: "CC — Creative Commons License",
    zh: "CC — 知识共享许可证",
  },
  by: {
    en: "CC-BY — Creative Commons Attribution",
    zh: "CC-BY — 知识共享署名许可证",
  },
  nc: {
    en: "CC-NC — Creative Commons Non-Commercial",
    zh: "CC-NC — 知识共享非商业性使用",
  },
};

interface ItemDetailDialogProps {
  dialogRef: React.RefObject<HTMLDialogElement | null>;
  item: DirectoryItem | null;
  lang: Locale;
  isStarred: boolean;
  onToggleStar: (id: string) => void;
  onSelectCategory: (
    sectionId: DirectoryItem["sectionId"],
    categorySlug: string,
    subgroupId?: string | null
  ) => void;
}

export function ItemDetailDialog({
  dialogRef,
  item,
  lang,
  isStarred,
  onToggleStar,
  onSelectCategory,
}: ItemDetailDialogProps) {
  // Fallback for browsers without native <dialog closedby="any"> support
  React.useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if ("closedBy" in HTMLDialogElement.prototype) return;

    const isOutside = (e: PointerEvent, el: HTMLDialogElement) => {
      const r = el.getBoundingClientRect();
      return (
        e.clientX < r.left ||
        e.clientX > r.right ||
        e.clientY < r.top ||
        e.clientY > r.bottom
      );
    };

    let pressedOutside = false;
    const onPointerDown = (e: PointerEvent) => {
      pressedOutside = isOutside(e, dialog);
    };
    const onPointerUp = (e: PointerEvent) => {
      if (pressedOutside && isOutside(e, dialog)) {
        dialog.close();
      }
    };

    dialog.addEventListener("pointerdown", onPointerDown);
    dialog.addEventListener("pointerup", onPointerUp);
    return () => {
      dialog.removeEventListener("pointerdown", onPointerDown);
      dialog.removeEventListener("pointerup", onPointerUp);
    };
  }, [dialogRef]);

  const title = item ? item.title[lang] || item.title.en : "";
  const description = item ? item.description[lang] || item.description.en : "";
  const sectionName = item
    ? item.sectionTitle[lang] || item.sectionTitle.en
    : "";
  const categoryName = item
    ? item.categoryTitle[lang] || item.categoryTitle.en
    : "";
  const subgroupName =
    item?.subgroup ? item.subgroup[lang] || item.subgroup.en : null;

  const githubUrl = item?.githubRepo
    ? `https://github.com/${item.githubRepo}`
    : null;
  const extensionLink = item
    ? item.secondaryLinks.find((l) =>
        l.url.includes("extensions.blender.org")
      )?.url ??
      (item.url?.includes("extensions.blender.org") ? item.url : null)
    : null;

  return (
    <dialog
      ref={dialogRef}
      closedby="any"
      aria-labelledby="item-detail-title"
      className="m-auto w-[min(580px,92vw)] max-h-[85vh] rounded-xl border border-border bg-card text-card-foreground p-0 shadow-2xl open:flex open:flex-col"
    >
      {item && (
        <>
          {/* Header */}
          <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
            <div className="min-w-0 flex-1 space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <h2
                  id="item-detail-title"
                  className="text-lg font-semibold tracking-tight text-foreground"
                >
                  {title}
                </h2>
                <Badge
                  variant={item.isPaid ? "outline" : "secondary"}
                  className="text-[11px]"
                >
                  {item.isPaid
                    ? lang === "zh"
                      ? "付费商业 (Paid)"
                      : "Paid / Commercial"
                    : lang === "zh"
                      ? "免费 (Free)"
                      : "Free"}
                </Badge>
              </div>

              <div className="flex items-center gap-1.5 text-xs text-muted-foreground flex-wrap">
                <FolderOpen className="size-3.5 shrink-0" />
                <span>{sectionName}</span>
                <span>/</span>
                <button
                  type="button"
                  onClick={() => {
                    onSelectCategory(item.sectionId, item.categorySlug, null);
                    dialogRef.current?.close();
                  }}
                  className="hover:text-foreground hover:underline underline-offset-4 cursor-pointer"
                >
                  {categoryName}
                </button>
                {subgroupName && (
                  <>
                    <span>/</span>
                    <button
                      type="button"
                      onClick={() => {
                        onSelectCategory(
                          item.sectionId,
                          item.categorySlug,
                          item.subgroupId
                        );
                        dialogRef.current?.close();
                      }}
                      className="hover:text-foreground hover:underline underline-offset-4 cursor-pointer"
                    >
                      {subgroupName}
                    </button>
                  </>
                )}
              </div>
            </div>

            <div className="flex items-center gap-1 shrink-0">
              <Button
                type="button"
                variant="outline"
                size="icon-sm"
                onClick={() => onToggleStar(item.id)}
                aria-pressed={isStarred}
                aria-label={isStarred ? "Remove from Saved" : "Save to Stack"}
              >
                <Bookmark
                  className={cn("size-3.5", isStarred && "fill-current")}
                />
              </Button>

              <form method="dialog">
                <Button
                  type="submit"
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Close detail dialog"
                  autoFocus
                >
                  <X className="size-4" />
                </Button>
              </form>
            </div>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            {/* Full Un-truncated Description */}
            <div className="space-y-1.5">
              <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {lang === "zh" ? "简介与说明" : "Description"}
              </h3>
              <p className="text-sm leading-relaxed text-foreground">
                {description}
              </p>
            </div>

            {/* Metadata & Licenses */}
            {(item.licenses.length > 0 ||
              extensionLink ||
              githubUrl ||
              item.secondaryLinks.length > 0) && (
              <div className="space-y-2.5 pt-2 border-t border-border/70">
                {item.licenses.length > 0 && (
                  <div className="flex items-start gap-2 text-xs">
                    <Scale className="size-4 text-muted-foreground shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <span className="font-medium text-foreground">
                        {lang === "zh" ? "开源与使用协议：" : "License:"}
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {item.licenses.map((lic) => (
                          <Badge key={lic} variant="outline" className="text-xs">
                            {LICENSE_DESCRIPTIONS[lic]
                              ? LICENSE_DESCRIPTIONS[lic][lang]
                              : lic.toUpperCase()}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Platform & Secondary Links */}
                <div className="space-y-1.5">
                  <span className="text-xs font-medium text-muted-foreground">
                    {lang === "zh" ? "相关链接与平台：" : "Links & Platforms:"}
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {extensionLink && (
                      <Button asChild variant="outline" size="xs">
                        <a
                          href={extensionLink}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Blocks className="size-3.5" />
                          <span>Blender Extensions Platform</span>
                          <ExternalLink className="size-3 opacity-60" />
                        </a>
                      </Button>
                    )}

                    {githubUrl && (
                      <Button asChild variant="outline" size="xs">
                        <a
                          href={githubUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <svg
                            viewBox="0 0 24 24"
                            fill="currentColor"
                            className="size-3.5"
                            aria-hidden="true"
                          >
                            <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
                          </svg>
                          <span>{item.githubRepo}</span>
                          <ExternalLink className="size-3 opacity-60" />
                        </a>
                      </Button>
                    )}

                    {item.secondaryLinks
                      .filter(
                        (l) =>
                          l.url !== extensionLink && l.url !== githubUrl
                      )
                      .map((l, idx) => (
                        <Button
                          key={`${l.url}-${idx}`}
                          asChild
                          variant="outline"
                          size="xs"
                        >
                          <a
                            href={l.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <span>{l.label[lang] || l.label.en}</span>
                            <ExternalLink className="size-3 opacity-60" />
                          </a>
                        </Button>
                      ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer with Primary External Link Button */}
          <div className="flex items-center justify-between gap-3 border-t border-border bg-muted/30 px-5 py-3.5">
            <form method="dialog">
              <Button type="submit" variant="outline" size="sm">
                {lang === "zh" ? "关闭" : "Close"}
              </Button>
            </form>

            {item.url && (
              <Button asChild size="sm">
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <span>
                    {lang === "zh" ? "访问官方网站 / 下载" : "Open Website / Download"}
                  </span>
                  <ArrowUpRight className="size-4" />
                </a>
              </Button>
            )}
          </div>
        </>
      )}
    </dialog>
  );
}
