import * as React from "react";
import { cn } from "@/lib/utils";

function Card({
  as: Comp = "div",
  className,
  ...props
}: React.HTMLAttributes<HTMLElement> & { as?: "div" | "article" }) {
  return (
    <Comp
      data-slot="card"
      className={cn(
        "bg-card text-card-foreground flex flex-col justify-between gap-3 rounded-xl border p-4 sm:p-5 shadow-2xs transition-colors min-w-0 overflow-hidden",
        className
      )}
      {...props}
    />
  );
}

function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn("flex items-center justify-between gap-2 min-w-0", className)}
      {...props}
    />
  );
}

function CardTitle({
  as: Comp = "div",
  className,
  ...props
}: React.HTMLAttributes<HTMLElement> & { as?: "div" | "h2" | "h3" }) {
  return (
    <Comp
      data-slot="card-title"
      className={cn("leading-snug font-semibold tracking-tight min-w-0 flex-1", className)}
      {...props}
    />
  );
}

function CardDescription({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="card-description"
      className={cn("text-foreground/80 text-sm leading-relaxed", className)}
      {...props}
    />
  );
}

function CardAction({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-action"
      className={cn("flex items-center gap-0.5 shrink-0", className)}
      {...props}
    />
  );
}

function CardContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-content"
      className={cn("flex-1 min-w-0", className)}
      {...props}
    />
  );
}

function CardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn(
        "flex flex-col items-stretch gap-2 pt-3 border-t border-border/70 min-w-0",
        className
      )}
      {...props}
    />
  );
}

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
};
