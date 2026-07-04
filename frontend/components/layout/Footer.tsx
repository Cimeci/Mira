import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * Trust-line footer pinned to the bottom of every screen. `mt-auto` lets the
 * screen stretch to fill the viewport with the footer at the true bottom.
 */
export function Footer({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <footer
      className={cn(
        "mt-auto flex w-full justify-center border-t border-[rgba(181,107,255,0.22)] bg-[rgba(20,14,31,0.6)] px-5 py-[14px] text-center text-caption text-mira-muted-dim",
        className
      )}
    >
      {children}
    </footer>
  );
}
