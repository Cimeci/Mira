import Link from "next/link";
import type { ReactNode } from "react";
import { GlowBackdrop } from "@/components/ui/GlowBackdrop";
import { Header } from "@/components/layout/Header";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { ScreenTitle } from "@/components/ui/ScreenTitle";

export const LEGAL_UPDATED = "july 5, 2026";

interface LegalNavLink {
  href: string;
  label: string;
}

/**
 * Shared chrome for the legal pages: breadcrumb, title, last-updated meta,
 * a readable article column, prev/next navigation between the three legal
 * documents, and the full site footer.
 */
export function LegalShell({
  title,
  intro,
  prev,
  next,
  children,
}: {
  title: string;
  intro: string;
  prev?: LegalNavLink;
  next?: LegalNavLink;
  children: ReactNode;
}) {
  return (
    <div className="relative mx-auto flex min-h-screen w-full max-w-[1440px] flex-col items-center overflow-hidden bg-mira-void">
      <GlowBackdrop />
      <Header />

      <main className="mb-20 mt-12 w-full max-w-[720px] px-6 lg:px-0">
        <nav aria-label="breadcrumb" className="text-caption text-mira-muted-dim">
          <Link
            href="/legal"
            className="underline-offset-4 transition-colors hover:text-mira-lilac-glow hover:underline"
          >
            legal
          </Link>
          <span aria-hidden> / </span>
          <span className="text-mira-muted-text">{title}</span>
        </nav>

        <article className="mt-6">
          <header className="flex flex-col gap-3 border-b border-[rgba(181,107,255,0.22)] pb-7">
            <ScreenTitle>{title}</ScreenTitle>
            <p className="text-caption uppercase tracking-label text-mira-muted-dim">
              last updated — {LEGAL_UPDATED}
            </p>
            <p className="text-body-sm leading-[1.7] text-mira-muted-text">
              {intro}
            </p>
          </header>

          <div className="mt-2 flex flex-col">{children}</div>
        </article>

        {(prev || next) && (
          <nav
            aria-label="legal pages"
            className="mt-14 flex items-center justify-between gap-4 border-t border-[rgba(181,107,255,0.22)] pt-6 text-body-sm"
          >
            {prev ? (
              <Link
                href={prev.href}
                className="text-mira-muted-text underline-offset-4 transition-colors hover:text-mira-lilac-glow hover:underline"
              >
                ← {prev.label}
              </Link>
            ) : (
              <span />
            )}
            {next && (
              <Link
                href={next.href}
                className="text-mira-muted-text underline-offset-4 transition-colors hover:text-mira-lilac-glow hover:underline"
              >
                {next.label} →
              </Link>
            )}
          </nav>
        )}
      </main>

      <div className="mt-auto w-full">
        <SiteFooter />
      </div>
    </div>
  );
}

/** Numbered article section: "01 · data we collect" heading + prose body. */
export function LegalSection({
  number,
  title,
  children,
}: {
  number: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section aria-label={title} className="border-b border-[rgba(181,107,255,0.12)] py-8 last:border-b-0">
      <h2 className="flex items-baseline gap-3">
        <span
          aria-hidden
          className="font-display text-[15px] text-mira-neon-purple [text-shadow:0_0_10px_rgba(107,47,165,0.6)]"
        >
          {number}
        </span>
        <span className="font-display text-[17px] lowercase leading-[1.3] tracking-display text-mira-lilac-glow">
          {title}
        </span>
      </h2>
      <div className="mt-4 flex flex-col gap-3 text-body-sm leading-[1.7] text-mira-muted-text [&_strong]:font-medium [&_strong]:text-mira-luminance [&_ul]:flex [&_ul]:list-none [&_ul]:flex-col [&_ul]:gap-2">
        {children}
      </div>
    </section>
  );
}

/** Pixel-bullet list item used inside LegalSection lists. */
export function LegalItem({ children }: { children: ReactNode }) {
  return (
    <li className="flex gap-3">
      <span aria-hidden className="mt-[2px] text-mira-electric-lilac">
        ▪
      </span>
      <span>{children}</span>
    </li>
  );
}
