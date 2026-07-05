import type { ReactNode } from "react";
import { GlowBackdrop } from "@/components/ui/GlowBackdrop";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

/**
 * Chrome for the returning-user dashboard (cases list + case detail). Unlike
 * ScreenShell this carries no intake progress bar and no scanlines — the
 * dashboard is a calm operational surface, not a brand or flow moment. A single
 * narrow reading column keeps the case list one-column and mobile-friendly.
 */
export function CasesShell({
  children,
  footer,
}: {
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <div className="relative mx-auto flex min-h-screen w-full max-w-[1440px] flex-col items-center overflow-hidden bg-mira-void">
      <GlowBackdrop />
      <Header />

      <main className="mb-14 mt-9 w-full max-w-[560px] px-5 sm:px-8">
        {children}
      </main>

      <Footer>{footer}</Footer>
    </div>
  );
}
