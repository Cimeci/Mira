import type { Metadata } from "next";
import Link from "next/link";
import { GlowBackdrop } from "@/components/ui/GlowBackdrop";
import { Header } from "@/components/layout/Header";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { ScreenTitle } from "@/components/ui/ScreenTitle";
import { LEGAL_UPDATED } from "@/components/legal/LegalShell";

export const metadata: Metadata = {
  title: "mira — legal",
  description: "legal notice, privacy policy, and terms for the mira prototype.",
};

const PAGES = [
  {
    href: "/legal/mentions",
    title: "legal notice",
    summary: "who publishes mira, where it is hosted, the mit license, and how to reach the team.",
  },
  {
    href: "/legal/privacy",
    title: "privacy",
    summary: "the minimum we collect, what we refuse to store, retention limits, and your gdpr rights.",
  },
  {
    href: "/legal/terms",
    title: "terms",
    summary: "the mandate you sign, the approvals mira waits for, and the limits of the prototype.",
  },
];

export default function LegalHubScreen() {
  return (
    <div className="relative mx-auto flex min-h-screen w-full max-w-[1440px] flex-col items-center overflow-hidden bg-mira-void">
      <GlowBackdrop />
      <Header />

      <main className="mb-20 mt-12 w-full max-w-[720px] px-6 lg:px-0">
        <div className="flex flex-col gap-3">
          <ScreenTitle>legal</ScreenTitle>
          <p className="text-caption uppercase tracking-label text-mira-muted-dim">
            last updated — {LEGAL_UPDATED}
          </p>
          <p className="text-body-sm leading-[1.7] text-mira-muted-text">
            everything mira commits to, in three short documents written to be
            read — not scrolled past.
          </p>
        </div>

        <nav aria-label="legal documents" className="mt-10 flex flex-col gap-5">
          {PAGES.map((page, index) => (
            <Link
              key={page.href}
              href={page.href}
              className="group flex items-start gap-5 rounded-card border border-[rgba(181,107,255,0.3)] bg-mira-night p-6 shadow-panel transition-all duration-300 hover:-translate-y-[2px] hover:border-mira-electric-lilac hover:shadow-border-glow"
            >
              <span
                aria-hidden
                className="font-display text-[26px] leading-none text-mira-neon-purple transition-colors group-hover:text-mira-electric-lilac [text-shadow:0_0_14px_rgba(107,47,165,0.6)]"
              >
                {String(index + 1).padStart(2, "0")}
              </span>
              <span className="flex flex-col gap-2">
                <span className="font-display text-[17px] lowercase tracking-display text-mira-lilac-glow">
                  {page.title}
                </span>
                <span className="text-body-sm leading-[1.6] text-mira-muted-text">
                  {page.summary}
                </span>
              </span>
              <span
                aria-hidden
                className="ml-auto self-center text-mira-muted-dim transition-all group-hover:translate-x-1 group-hover:text-mira-lilac-glow"
              >
                →
              </span>
            </Link>
          ))}
        </nav>
      </main>

      <div className="mt-auto w-full">
        <SiteFooter />
      </div>
    </div>
  );
}
