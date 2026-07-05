const STEPS = [
  {
    number: "01",
    title: "tell mira what happened",
    body: "paste the urls, say how you found them, and sign a mandate scoped to this case only. no identity document required.",
  },
  {
    number: "02",
    title: "mira acts in your name",
    body: "evidence is sealed as perceptual hashes, the platform is notified, the host escalated. every external step waits for your explicit approval.",
  },
  {
    number: "03",
    title: "it comes down — and stays down",
    body: "takedowns are tracked on your case timeline, and reuploads are caught automatically so you never have to look again.",
  },
];

/** Landing explainer: three numbered steps from report to takedown. */
export function HowItWorks() {
  return (
    <section
      id="how"
      aria-labelledby="how-heading"
      className="w-full max-w-[1080px] scroll-mt-10 px-6 pb-24 pt-24"
    >
      <div className="flex flex-col items-center gap-3 text-center">
        <p className="text-label uppercase tracking-label text-mira-muted-text">
          from report to takedown
        </p>
        <h2
          id="how-heading"
          className="font-display text-[clamp(20px,3vw,28px)] lowercase leading-[1.2] tracking-display text-mira-lilac-glow text-shadow-glow"
        >
          how mira works
        </h2>
      </div>

      <ol className="mt-12 grid gap-5 md:grid-cols-3">
        {STEPS.map((step) => (
          <li
            key={step.number}
            className="group flex flex-col gap-4 rounded-card border border-[rgba(181,107,255,0.3)] bg-mira-night p-7 shadow-panel transition-all duration-300 hover:-translate-y-1 hover:border-mira-electric-lilac hover:shadow-border-glow"
          >
            <span
              aria-hidden
              className="font-display text-[30px] leading-none text-mira-neon-purple transition-colors group-hover:text-mira-electric-lilac [text-shadow:0_0_14px_rgba(107,47,165,0.6)]"
            >
              {step.number}
            </span>
            <h3 className="text-body-lg font-medium lowercase text-mira-luminance">
              {step.title}
            </h3>
            <p className="text-body-sm leading-[1.6] text-mira-muted-text">
              {step.body}
            </p>
          </li>
        ))}
      </ol>

      <p className="mt-14 flex items-center justify-center gap-3 text-center text-body-sm leading-[1.45] text-mira-muted-text">
        <span className="text-mira-lilac-glow">◆</span>
        <span>
          mira handles the process. you stay in control of every legal step —
          nothing is filed without your approval.
        </span>
        <span className="inline-block h-[15px] w-2 animate-blink bg-mira-electric-lilac shadow-glow-soft" />
      </p>
    </section>
  );
}
