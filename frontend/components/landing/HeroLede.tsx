/**
 * Hero sub-lede — the plain-language "what mira is", set just under the CRT
 * punchline so a first-time visitor understands the product in a single read.
 * Kept verb-light on purpose: the TypedTerminal below animates the actions.
 */
export function HeroLede() {
  return (
    <p className="mt-6 max-w-[52ch] text-balance px-2 text-center text-body-sm leading-[1.7] text-mira-muted-text">
      a <span className="text-mira-lilac-glow">consent-first takedown agent</span>{" "}
      for non-consensual intimate images and sexual deepfakes. point it at the
      abuse — mira does the rest, and you stay in control of every step.
    </p>
  );
}
