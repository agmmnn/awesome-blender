/// <reference types="vite/client" />
import * as React from "react";
import {
  HeadContent,
  Outlet,
  Scripts,
  createRootRoute,
  useRouterState,
} from "@tanstack/react-router";
import { OG_IMAGE_URL, SITE_NAME } from "@/lib/seo";
import appCss from "@/styles/app.css?url";

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { name: "color-scheme", content: "light dark" },
      {
        name: "theme-color",
        media: "(prefers-color-scheme: light)",
        content: "#ffffff",
      },
      {
        name: "theme-color",
        media: "(prefers-color-scheme: dark)",
        content: "#1b1b1f",
      },
      {
        name: "robots",
        content:
          "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1",
      },
      {
        title:
          "Awesome Blender — Curated Directory of Add-ons, Assets & Tools",
      },
      {
        name: "description",
        content:
          "A curated directory of downloadable Blender add-ons, official extensions, 3D assets, HDRIs, and standalone tools.",
      },
      { property: "og:type", content: "website" },
      { property: "og:site_name", content: SITE_NAME },
      { property: "og:image", content: OG_IMAGE_URL },
      {
        property: "og:image:alt",
        content: "Awesome Blender curated directory preview",
      },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:image", content: OG_IMAGE_URL },
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "icon", href: "/imgs/blender.svg", type: "image/svg+xml" },
      { rel: "apple-touch-icon", href: "/logo.png" },
      { rel: "manifest", href: "/manifest.webmanifest" },
    ],
  }),
  component: RootComponent,
});

function RootComponent() {
  const lang = useRouterState({
    select: (s) => (s.location.search as { lang?: string } | undefined)?.lang,
  });

  return (
    <html lang={lang === "zh" ? "zh-CN" : "en"} suppressHydrationWarning>
      <head>
        <HeadContent />
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var m=document.querySelector('meta[name="color-scheme"]');if(m)m.content=localStorage.getItem("color-scheme")??"light dark";}catch(e){}`,
          }}
        />
      </head>
      <body className="min-h-screen bg-background text-foreground font-sans antialiased selection:bg-primary selection:text-primary-foreground">
        <Outlet />
        <Scripts />
      </body>
    </html>
  );
}
