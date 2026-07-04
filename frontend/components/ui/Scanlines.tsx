import { cn } from "@/lib/cn";

/**
 * CRT scanline overlay. Per the design system, scanlines apply to brand
 * moments only. Renders an absolutely-positioned overlay; the parent must be
 * positioned. `variant="band"` is the landing's top gradient band.
 */
export function Scanlines({
  className,
  variant = "fill",
}: {
  className?: string;
  variant?: "fill" | "band";
}) {
  return (
    <div
      aria-hidden
      className={cn(
        "pointer-events-none [background:repeating-linear-gradient(to_bottom,rgba(242,230,255,0.06)_0px,rgba(242,230,255,0.06)_1px,transparent_2px,transparent_5px)] [mix-blend-mode:screen]",
        variant === "band"
          ? "absolute inset-x-0 top-0 h-[460px] opacity-[0.35]"
          : "absolute inset-0 opacity-[0.35]",
        className
      )}
    />
  );
}
