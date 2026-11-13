import * as React from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";

function getSystemScheme(): "dark" | "light" {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function getRenderedScheme(): "dark" | "light" {
  if (typeof document === "undefined") return "dark";
  const meta = document.querySelector<HTMLMetaElement>(
    'meta[name="color-scheme"]'
  );
  const content = meta?.content;
  if (content === "dark" || content === "light") {
    return content;
  }
  return getSystemScheme();
}

export function ThemeToggle() {
  const [scheme, setScheme] = React.useState<"dark" | "light">("dark");

  React.useEffect(() => {
    const sync = () => setScheme(getRenderedScheme());
    sync();

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onStorage = (e: StorageEvent) => {
      if (e.key === "color-scheme") {
        const meta = document.querySelector<HTMLMetaElement>(
          'meta[name="color-scheme"]'
        );
        if (meta) {
          meta.content = e.newValue ?? "light dark";
        }
        sync();
      }
    };

    mq.addEventListener("change", sync);
    window.addEventListener("storage", onStorage);
    return () => {
      mq.removeEventListener("change", sync);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const handleToggle = () => {
    const meta = document.querySelector<HTMLMetaElement>(
      'meta[name="color-scheme"]'
    );
    if (!meta) return;

    const current = getRenderedScheme();
    const target: "dark" | "light" = current === "dark" ? "light" : "dark";
    const sys = getSystemScheme();

    try {
      if (target !== sys) {
        localStorage.setItem("color-scheme", target);
        meta.content = target;
      } else {
        localStorage.removeItem("color-scheme");
        meta.content = "light dark";
      }
    } catch {
      meta.content = target;
    }

    setScheme(target);
  };

  return (
    <Button
      type="button"
      variant="outline"
      size="icon"
      onClick={handleToggle}
      aria-label={
        scheme === "dark" ? "Switch to light theme" : "Switch to dark theme"
      }
      title={
        scheme === "dark" ? "Switch to light theme" : "Switch to dark theme"
      }
    >
      {scheme === "dark" ? (
        <Sun className="size-4" />
      ) : (
        <Moon className="size-4" />
      )}
    </Button>
  );
}
