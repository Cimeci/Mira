import { ScreenShell } from "@/components/layout/ScreenShell";
import { SessionGate } from "@/components/auth/SessionGate";
import { ScreenTitle } from "@/components/ui/ScreenTitle";
import { LinkButton } from "@/components/ui/LinkButton";
import { BackButton } from "@/components/ui/BackButton";
import { CaseCard } from "@/components/case/CaseCard";
import { CaseTimeline } from "@/components/case/CaseTimeline";

export default function CaseCreatedScreen() {
  return (
    <SessionGate>
      <ScreenShell
        progress={{ label: "case open", filled: 5 }}
        contentWidth={860}
        centered
        footer="mira is handling it — you never have to look again."
      >
        <div className="flex flex-col gap-14 md:flex-row md:items-start">
          <div className="flex w-full flex-col gap-[22px] md:w-[400px] md:flex-shrink-0">
            <ScreenTitle>your case is open ✓</ScreenTitle>

            <CaseCard />

            <p className="text-[14px] leading-[1.5] text-mira-muted-text">
              our scout is now collecting and verifying evidence. we&rsquo;ll notify
              you before any step that needs your approval.
            </p>

            <div className="flex items-center gap-[14px]">
              <BackButton href="/signature" />
              <LinkButton href="/" variant="primary" className="px-9">
                go to case dashboard
              </LinkButton>
            </div>
          </div>

          <CaseTimeline />
        </div>
      </ScreenShell>
    </SessionGate>
  );
}
