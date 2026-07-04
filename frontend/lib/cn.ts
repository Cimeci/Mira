/** Tiny className joiner — filters falsy values, joins with spaces. */
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}
