const GUARANTEES = [
  {
    label: "consent-first",
    body: "nothing runs without a mandate you sign. revoke it and the whole case is purged.",
  },
  {
    label: "scope-locked",
    body: "mira only ever opens the urls you hand it — never the open web.",
  },
  {
    label: "images never stored",
    body: "evidence is kept as perceptual hashes and on-device embeddings, never the pictures.",
  },
  {
    label: "you approve every send",
    body: "no report, notice, or email leaves without your explicit go-ahead.",
  },
  {
    label: "minors protected",
    body: "any hint of a minor halts the case and escalates to the authorities. zero storage.",
  },
  {
    label: "open source",
    body: "mit-licensed and auditable end to end. nothing about mira is a black box.",
  },
];

/**
 * The guarantees grid — mira's guardrails surfaced as promises. This is the
 * trust argument (consent, scope, minimization, minor-safety, transparency).
 * The 1px gap over a lilac backdrop draws hairline rules between cells, so it
 * reads as one panel rather than a uniform stack of cards.
 */
export function Guarantees() {
  return (
    <section
      aria-labelledby="guarantees-heading"
      className="w-full max-w-[1080px] px-6 pb-24 pt-8"
    >
      <div className="flex flex-col items-center gap-3 text-center">
        <p className="text-label uppercase tracking-label text-mira-muted-text">
          built consent-first
        </p>
        <h2
          id="guarantees-heading"
          className="font-display text-[clamp(20px,3vw,28px)] lowercase leading-[1.2] tracking-display text-mira-lilac-glow text-shadow-glow"
        >
          the guarantees mira runs on
        </h2>
      </div>

      <ul className="mt-12 grid gap-px overflow-hidden rounded-card border border-[rgba(181,107,255,0.3)] bg-[rgba(181,107,255,0.16)] shadow-panel sm:grid-cols-2 lg:grid-cols-3">
        {GUARANTEES.map((g) => (
          <li
            key={g.label}
            className="group flex flex-col gap-2.5 bg-mira-night p-6 transition-colors duration-300 hover:bg-mira-purple-steel"
          >
            <div className="flex items-center gap-2.5">
              <span
                aria-hidden
                className="text-mira-electric-lilac transition-transform duration-300 [text-shadow:0_0_10px_rgba(181,107,255,0.7)] group-hover:scale-110"
              >
                ◆
              </span>
              <h3 className="font-display text-[13px] lowercase tracking-display text-mira-lilac-glow">
                {g.label}
              </h3>
            </div>
            <p className="text-body-sm leading-[1.6] text-mira-muted-text">
              {g.body}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
