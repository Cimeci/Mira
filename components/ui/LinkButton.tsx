import Link, { type LinkProps } from "next/link";
import type { ReactNode } from "react";
import {
  buttonClasses,
  type ButtonSize,
  type ButtonVariant,
} from "./Button";

/**
 * A navigation styled as a button. Flow transitions ("continue", "back",
 * "start a case") are real route changes, so they render as anchors for
 * correct semantics and keyboard behavior.
 */
export function LinkButton({
  variant = "primary",
  size = "lg",
  className,
  children,
  ...linkProps
}: LinkProps & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
  children: ReactNode;
  "aria-label"?: string;
}) {
  return (
    <Link className={buttonClasses(variant, size, className)} {...linkProps}>
      {children}
    </Link>
  );
}
