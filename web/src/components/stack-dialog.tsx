import * as React from "react";
import { Check, Copy, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { DirectoryItem, Locale } from "@/lib/catalog";

interface StackDialogProps {
  dialogRef: React.RefObject<HTMLDialogElement | null>;
  items: DirectoryItem[];
  lang: Locale;
  onRemoveItem: (id: string) => void;
  onClearAll: () => void;
}

export function StackDialog({
  dialogRef,
  items,
  lang,
  onRemoveItem,
  onClearAll,
}: StackDialogProps) {
  const [copied, setCopied] = React.useState(false);

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

  const markdownExport = React.useMemo(() => {
    if (items.length === 0) return "";
    const lines = ["# My Blender Stack", ""];
    for (const item of items) {
      const title = item.title[lang] || item.title.en;
      const desc = item.description[lang] || item.description.en;
      lines.push(`- [${title}](${item.url}) - ${desc}`);
    }
    return lines.join("\n");
  }, [items, lang]);

  const handleCopyMarkdown = async () => {
    if (!markdownExport) return;
    await navigator.clipboard.writeText(markdownExport);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <dialog
      ref={dialogRef}
      closedby="any"
      aria-labelledby="saved-stack-title"
      className="m-auto w-[min(640px,92vw)] max-h-[82vh] rounded-xl border border-border bg-card text-card-foreground p-0 shadow-xl open:flex open:flex-col"
    >
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div className="flex items-center gap-2">
          <h2 id="saved-stack-title" className="text-base font-semibold">
            {lang === "zh" ? "已保存的工具包" : "Saved Blender Stack"}
          </h2>
          <Badge variant="secondary">{items.length}</Badge>
        </div>

        <form method="dialog">
          <Button
            type="submit"
            variant="ghost"
            size="icon-sm"
            aria-label="Close dialog"
            autoFocus
          >
            <X className="size-4" />
          </Button>
        </form>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-3">
        {items.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border py-12 text-center text-sm text-muted-foreground">
            {lang === "zh"
              ? "尚未收藏任何插件或资源。点击卡片右上角的书签图标即可添加。"
              : "No items saved yet. Click the bookmark icon on any card to build your personal Blender stack."}
          </div>
        ) : (
          <div className="divide-y divide-border rounded-lg border border-border bg-background">
            {items.map((item) => {
              const title = item.title[lang] || item.title.en;
              const cat = item.categoryTitle[lang] || item.categoryTitle.en;
              return (
                <div
                  key={item.id}
                  className="flex items-center justify-between gap-3 px-3.5 py-2.5 text-sm"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <a
                        href={item.url ?? "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium hover:underline truncate"
                      >
                        {title}
                      </a>
                      <Badge
                        variant="secondary"
                        className="text-[10px] font-normal px-1.5 py-0"
                      >
                        {cat}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground truncate mt-0.5">
                      {item.description[lang] || item.description.en}
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => onRemoveItem(item.id)}
                    aria-label={`Remove ${title}`}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <X className="size-3.5" />
                  </Button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between gap-2 border-t border-border px-5 py-3.5 bg-muted/30">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          disabled={items.length === 0}
          onClick={onClearAll}
          className="text-muted-foreground hover:text-destructive"
        >
          <Trash2 className="size-3.5" />
          {lang === "zh" ? "清空" : "Clear all"}
        </Button>

        <Button
          type="button"
          size="sm"
          disabled={items.length === 0}
          onClick={handleCopyMarkdown}
        >
          <span
            className="inline-flex items-center gap-1.5 transition-[filter,opacity] duration-150 ease-out"
            style={{
              filter: copied ? "blur(0px)" : undefined,
            }}
          >
            {copied ? (
              <>
                <Check className="size-3.5" />
                {lang === "zh" ? "已复制 Markdown" : "Copied Markdown"}
              </>
            ) : (
              <>
                <Copy className="size-3.5" />
                {lang === "zh" ? "复制为 Markdown" : "Copy as Markdown"}
              </>
            )}
          </span>
        </Button>
      </div>
    </dialog>
  );
}
