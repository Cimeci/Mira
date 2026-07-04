import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/** The Silkscreen section title used at the head of each inner screen. */
export function ScreenTitle({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <h1
      className={cn(
        "text-shadow-title font-display text-[28px] leading-[1.2] text-mira-lilac-glow",
        className
      )}
    >
      {children}
    </h1>
  );
}
