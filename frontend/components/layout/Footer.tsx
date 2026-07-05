import type { ReactNode } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";

const LEGAL_LINKS = [
  { href: "/legal/mentions", label: "legal notice" },
  { href: "/legal/privacy", label: "privacy" },
  { href: "/legal/terms", label: "terms" },
] as const;

/**
 * Trust-line footer pinned to the bottom of every screen, with the legal
 * links row underneath. `mt-auto` lets the screen stretch to fill the
 * viewport with the footer at the true bottom.
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
        "mt-auto flex w-full flex-col items-center gap-2 border-t border-[rgba(181,107,255,0.22)] bg-[rgba(20,14,31,0.6)] px-5 py-[14px] text-center text-caption text-mira-muted-dim",
        className
      )}
    >
      <div className="flex justify-center">{children}</div>
      <nav
        aria-label="legal"
        className="flex items-center gap-2 text-caption text-mira-muted-dim"
      >
        {LEGAL_LINKS.map(({ href, label }, index) => (
          <span key={href} className="flex items-center gap-2">
            {index > 0 && <span aria-hidden>·</span>}
            <Link
              href={href}
              className="underline-offset-4 transition-colors hover:text-mira-lilac-glow hover:underline"
            >
              {label}
            </Link>
          </span>
        ))}
      </nav>
    </footer>
  );
}
