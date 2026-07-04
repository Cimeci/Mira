import { cn } from "@/lib/cn";

/**
 * The soft radial purple glow blob anchored near the top of each screen.
 * `large` matches the taller landing halo; default matches the inner screens.
 */
export function GlowBackdrop({ large = false }: { large?: boolean }) {
  return (
    <div
      aria-hidden
      className={cn(
        "pointer-events-none absolute left-1/2 -translate-x-1/2",
        large
          ? "-top-[180px] h-[620px] w-[900px] bg-[radial-gradient(ellipse_at_center,rgba(107,47,165,0.35)_0%,rgba(107,47,165,0.12)_45%,transparent_70%)]"
          : "-top-[160px] h-[480px] w-[800px] bg-[radial-gradient(ellipse_at_center,rgba(107,47,165,0.28)_0%,transparent_70%)]"
      )}
    />
  );
}
