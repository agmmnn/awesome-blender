import * as React from "react";
import { cn } from "@/lib/utils";

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "placeholder:text-muted-foreground border-input bg-background flex h-9 w-full min-w-0 rounded-md border px-3 py-1 text-sm shadow-2xs transition-colors outline-none disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30 [&::-webkit-search-cancel-button]:hidden [&::-webkit-search-decoration]:hidden",
        className
      )}
      {...props}
    />
  );
}

export { Input };
