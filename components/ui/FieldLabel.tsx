import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/** Uppercase lilac field label used above form controls. */
export function FieldLabel({
  children,
  className,
  htmlFor,
}: {
  children: ReactNode;
  className?: string;
  htmlFor?: string;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className={cn(
        "text-[14px] uppercase tracking-[0.06em] text-mira-lilac-glow",
        className
      )}
    >
      {children}
    </label>
  );
}
