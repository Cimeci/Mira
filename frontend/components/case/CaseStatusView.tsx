import { ScreenShell } from "@/components/layout/ScreenShell";
import { ScreenTitle } from "@/components/ui/ScreenTitle";
import { LinkButton } from "@/components/ui/LinkButton";
import { CaseCard } from "./CaseCard";
import {
  CaseTimeline,
  DEFAULT_TIMELINE_STEPS,
  type TimelineStep,
} from "./CaseTimeline";

/**
 * The "your case is open" screen, shared by two entry points: the end of the
 * case-creation flow and the /cases/:caseId detail route. Content is driven by
 * props (case id, target label, status, timeline steps); the layout is
 * identical in both places. Defaults reproduce the intake screen exactly.
 */
export function CaseStatusView({
  caseId = "mira-4821",
  targetLabel = "[url]",
  status = "evidence collection started",
  steps = DEFAULT_TIMELINE_STEPS,
}: {
  caseId?: string;
  targetLabel?: string;
  status?: string;
  steps?: TimelineStep[];
}) {
  return (
    <ScreenShell
      progress={{ label: "case open", filled: 5 }}
      contentWidth={860}
      centered
      footer="mira is handling it — you never have to look again."
    >
      <div className="flex flex-col gap-14 md:flex-row md:items-start">
        <div className="flex w-full flex-col gap-[22px] md:w-[400px] md:flex-shrink-0">
          <ScreenTitle>your case is open ✓</ScreenTitle>

          <CaseCard caseId={caseId} targetLabel={targetLabel} status={status} />

          <p className="text-[14px] leading-[1.5] text-mira-muted-text">
            our scout is now collecting and verifying evidence. we&rsquo;ll notify
            you before any step that needs your approval.
          </p>

          <div className="flex items-center gap-[14px]">
            <LinkButton href="/cases" variant="primary" className="px-9">
              go to case dashboard
            </LinkButton>
          </div>
        </div>

        <CaseTimeline steps={steps} />
      </div>
    </ScreenShell>
  );
}
