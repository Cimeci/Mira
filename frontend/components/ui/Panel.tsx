import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

/** Night-surface bordered panel used for cards, form groups, and info blocks. */
export function Panel({
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-card border border-[rgba(181,107,255,0.35)] bg-mira-night",
        className
      )}
      {...rest}
    />
  );
}
