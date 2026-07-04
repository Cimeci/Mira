import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export type ButtonVariant = "flow" | "primary" | "ghost";
export type ButtonSize = "lg" | "md" | "sm";

const base =
  "mira-clip inline-flex items-center justify-center whitespace-nowrap font-display uppercase tracking-label cursor-pointer transition-colors disabled:cursor-not-allowed";

const sizes: Record<ButtonSize, string> = {
  lg: "min-h-[48px] px-11 text-label",
  md: "min-h-[40px] px-6 text-label",
  sm: "min-h-[36px] px-[22px] text-[11px]",
};

const variants: Record<ButtonVariant, string> = {
  // flowing neon gradient CTA — the "hot" primary action
  flow: "mira-cta-flow border border-mira-electric-lilac text-mira-luminance text-shadow-glow shadow-[0_0_0_1px_rgba(181,107,255,0.9),0_0_12px_rgba(181,107,255,0.55),0_0_26px_rgba(107,47,165,0.45)] hover:border-mira-lilac-glow",
  // solid, glowing-outline primary
  primary:
    "border border-mira-electric-lilac bg-mira-night text-mira-lilac-glow text-shadow-glow shadow-border-glow hover:bg-mira-purple-steel hover:text-mira-luminance",
  // quiet outline (secondary / back)
  ghost:
    "border border-[rgba(181,107,255,0.45)] bg-transparent text-mira-muted-text hover:border-mira-electric-lilac hover:bg-mira-purple-steel hover:text-mira-lilac-glow",
};

/** Shared class builder so both <button> and navigation <Link> can wear it. */
export function buttonClasses(
  variant: ButtonVariant = "primary",
  size: ButtonSize = "lg",
  className?: string
) {
  return cn(base, sizes[size], variants[variant], className);
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "lg", className, type, ...rest }, ref) => (
    <button
      ref={ref}
      type={type ?? "button"}
      className={buttonClasses(variant, size, className)}
      {...rest}
    />
  )
);

Button.displayName = "Button";
