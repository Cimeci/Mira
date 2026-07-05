import { GlowBackdrop } from "@/components/ui/GlowBackdrop";
import { Scanlines } from "@/components/ui/Scanlines";
import { LinkButton } from "@/components/ui/LinkButton";
import { Wordmark } from "@/components/landing/Wordmark";
import { Punchline } from "@/components/landing/Punchline";
import { HeroLede } from "@/components/landing/HeroLede";
import { TypedTerminal } from "@/components/landing/TypedTerminal";
import { WhyMira } from "@/components/landing/WhyMira";
import { Guarantees } from "@/components/landing/Guarantees";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { ImpactCounters } from "@/components/landing/ImpactCounters";
import { SiteFooter } from "@/components/layout/SiteFooter";

export default function LandingScreen() {
  return (
    <div className="relative mx-auto flex w-full max-w-[1440px] flex-col items-center overflow-hidden bg-mira-void">
      <GlowBackdrop large />
      <Scanlines variant="band" />

      {/* hero fills the first viewport; the scroll cue hints at the rest */}
      <section
        aria-label="mira — you never have to look again"
        className="relative flex min-h-[100svh] w-full flex-col items-center justify-center px-5 pb-14 pt-10"
      >
        <Wordmark />
        <Punchline />
        <HeroLede />
        <TypedTerminal />

        <div className="mt-14 flex flex-col items-center gap-4">
          <LinkButton href="/start" variant="flow" className="px-32">
            start a case
          </LinkButton>
          <LinkButton
            href="/cases"
            variant="ghost"
            size="sm"
            className="text-mira-muted-text"
          >
            i already have a case
          </LinkButton>
        </div>

        <a
          href="#why"
          className="mt-16 flex animate-softpulse flex-col items-center gap-1 text-caption uppercase tracking-label text-mira-muted-dim transition-colors hover:text-mira-lilac-glow"
        >
          <span>why mira exists</span>
          <span aria-hidden>↓</span>
        </a>
      </section>

      <WhyMira />
      <Guarantees />
      <HowItWorks />

      {/* proof band: the live case counters, before the footer */}
      <section
        aria-label="mira in numbers"
        className="flex w-full flex-col items-center px-6 pb-28"
      >
        <ImpactCounters />
      </section>

      <SiteFooter />
    </div>
  );
}
