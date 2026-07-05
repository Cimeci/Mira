/**
 * "Why mira exists" — the editorial heart of the landing. Names the problem
 * (the second trauma of handling removal yourself) and mira's answer, in a
 * two-column layout that deliberately breaks the otherwise-centered rhythm.
 */
export function WhyMira() {
  return (
    <section
      id="why"
      aria-labelledby="why-heading"
      className="w-full max-w-[1080px] scroll-mt-10 px-6 pb-10 pt-24"
    >
      <div className="grid gap-8 md:grid-cols-[0.85fr_1.15fr] md:gap-14">
        <div className="flex flex-col gap-4">
          <p className="text-label uppercase tracking-label text-mira-muted-text">
            why mira exists
          </p>
          <h2
            id="why-heading"
            className="font-display text-[clamp(19px,2.8vw,30px)] lowercase leading-[1.28] tracking-display text-mira-lilac-glow text-shadow-glow"
          >
            being a victim is one trauma. handling the takedown yourself is a
            second.
          </h2>
        </div>

        <div className="flex flex-col gap-5 text-body-lg leading-[1.7] text-mira-muted-text">
          <p>
            finding the content, tracking down who hosts it, writing a legal
            notice that holds up, chasing every reupload — today that work falls
            on the person it hurt most, one painful step at a time.
          </p>
          <p className="text-mira-luminance">
            mira does the parts an agent can do without flinching, so you never
            have to relive it. you point, you approve — mira acts in your name.
          </p>
        </div>
      </div>
    </section>
  );
}
