import * as React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ScrollablePillBarProps {
  children: React.ReactNode;
  ariaLabel: string;
  className?: string;
}

export function ScrollablePillBar({
  children,
  ariaLabel,
  className,
}: ScrollablePillBarProps) {
  const scrollerRef = React.useRef<HTMLDivElement | null>(null);
  const [canScrollLeft, setCanScrollLeft] = React.useState(false);
  const [canScrollRight, setCanScrollRight] = React.useState(false);

  const updateScrollState = React.useCallback(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const { scrollLeft, scrollWidth, clientWidth } = el;
    setCanScrollLeft(scrollLeft > 4);
    setCanScrollRight(scrollLeft + clientWidth < scrollWidth - 4);
  }, []);

  React.useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    updateScrollState();

    const ro = new ResizeObserver(updateScrollState);
    ro.observe(el);
    window.addEventListener("resize", updateScrollState);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", updateScrollState);
    };
  }, [updateScrollState, children]);

  const scrollByAmount = (dir: -1 | 1) => {
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollBy({
      left: dir * Math.max(240, Math.floor(el.clientWidth * 0.55)),
      behavior: "smooth",
    });
  };

  return (
    <div className={cn("relative flex items-center min-w-0 w-full", className)}>
      {canScrollLeft && (
        <div className="pointer-events-none absolute left-0 top-0 bottom-0 z-10 flex items-center bg-gradient-to-r from-background via-background/90 to-transparent pr-6">
          <Button
            type="button"
            variant="outline"
            size="icon-sm"
            onClick={() => scrollByAmount(-1)}
            aria-label="Scroll categories left"
            className="pointer-events-auto size-7 rounded-full shadow-xs bg-background"
          >
            <ChevronLeft className="size-3.5" />
          </Button>
        </div>
      )}

      <div
        ref={scrollerRef}
        onScroll={updateScrollState}
        role="tablist"
        aria-label={ariaLabel}
        className="no-scrollbar flex items-center gap-1.5 overflow-x-auto scroll-smooth py-0.5 min-w-0 w-full"
      >
        {children}
      </div>

      {canScrollRight && (
        <div className="pointer-events-none absolute right-0 top-0 bottom-0 z-10 flex items-center justify-end bg-gradient-to-l from-background via-background/90 to-transparent pl-6">
          <Button
            type="button"
            variant="outline"
            size="icon-sm"
            onClick={() => scrollByAmount(1)}
            aria-label="Scroll categories right"
            className="pointer-events-auto size-7 rounded-full shadow-xs bg-background"
          >
            <ChevronRight className="size-3.5" />
          </Button>
        </div>
      )}
    </div>
  );
}
