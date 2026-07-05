import { GlowBackdrop } from "@/components/ui/GlowBackdrop";
import { Scanlines } from "@/components/ui/Scanlines";
import { LinkButton } from "@/components/ui/LinkButton";
import { Wordmark } from "@/components/landing/Wordmark";
import { Punchline } from "@/components/landing/Punchline";
import { TypedTerminal } from "@/components/landing/TypedTerminal";
import { ImpactCounters } from "@/components/landing/ImpactCounters";

export default function LandingScreen() {
  return (
    <div className="relative mx-auto flex min-h-screen w-full max-w-[1440px] flex-col items-center overflow-hidden bg-mira-void px-5">
      <GlowBackdrop large />
      <Scanlines variant="band" />

      <Wordmark />
      <Punchline />
      <TypedTerminal />
      <ImpactCounters />

      <div className="mt-11 flex flex-col items-center gap-4">
        <LinkButton href="/start" variant="flow" className="px-11">
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

      <footer className="mt-auto flex w-full justify-center border-t border-[rgba(181,107,255,0.22)] bg-[rgba(20,14,31,0.6)] px-5 py-[18px]">
        <div className="flex items-center gap-3 text-body-sm leading-[1.45] text-mira-muted-text">
          <span className="text-mira-lilac-glow">◆</span>
          <span>
            mira handles the process. you stay in control of every legal step —
            nothing is filed without your approval.
          </span>
          <span className="inline-block h-[15px] w-2 animate-blink bg-mira-electric-lilac shadow-glow-soft" />
        </div>
      </footer>
    </div>
  );
}
