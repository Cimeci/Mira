import type { LinkProps } from "next/link";
import type { ReactNode } from "react";
import { LinkButton } from "./LinkButton";

/** The recurring quiet "← back" navigation. */
export function BackButton(
  props: LinkProps & { className?: string; children?: ReactNode }
) {
  return (
    <LinkButton variant="ghost" size="md" {...props}>
      ← back
    </LinkButton>
  );
}
