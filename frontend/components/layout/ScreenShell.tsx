import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { GlowBackdrop } from "@/components/ui/GlowBackdrop";
import { Header } from "./Header";
import { Footer } from "./Footer";
import { ProgressBar } from "./ProgressBar";

/**
 * Shared chrome for the inner flow screens (start → case created):
 * background + glow, header bar, a full-width progress row, a centered content
 * column, and the trust-line footer. `centered` vertically centers the content
 * between the progress row and footer (screens 1, 2, 5); the taller screens
 * (3, 4) flow from the top instead.
 */
export function ScreenShell({
  progress,
  contentWidth,
  centered = false,
  footer,
  children,
}: {
  progress: { label: string; filled: number };
  contentWidth: number;
  centered?: boolean;
  footer: ReactNode;
  children: ReactNode;
}) {
  const widthStyle = { maxWidth: contentWidth };

  return (
    <div className="relative mx-auto flex min-h-screen w-full max-w-[1440px] flex-col items-center overflow-hidden bg-mira-void">
      <GlowBackdrop />
      <Header />

      <div
        style={widthStyle}
        className="mt-7 w-full px-5 sm:px-10 lg:px-0"
      >
        <ProgressBar label={progress.label} filled={progress.filled} />
      </div>

      <main
        style={widthStyle}
        className={cn(
          "relative w-full px-5 sm:px-10 lg:px-0",
          centered ? "mt-auto" : "mt-7 mb-14"
        )}
      >
        {children}
      </main>

      <Footer>{footer}</Footer>
    </div>
  );
}
