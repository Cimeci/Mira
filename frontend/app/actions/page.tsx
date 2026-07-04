import { ScreenShell } from "@/components/layout/ScreenShell";
import { SessionGate } from "@/components/auth/SessionGate";
import { ScreenTitle } from "@/components/ui/ScreenTitle";
import { LinkButton } from "@/components/ui/LinkButton";
import { BackButton } from "@/components/ui/BackButton";
import { ActionsPanel } from "@/components/actions/ActionsPanel";

export default function ActionOptionsScreen() {
  return (
    <SessionGate>
      <ScreenShell
        progress={{ label: "choose your actions", filled: 2 }}
        contentWidth={720}
        centered
        footer="nothing is sent without your approval."
      >
        <div className="flex flex-col gap-[18px]">
          <ScreenTitle>how do you want to act?</ScreenTitle>

          <ActionsPanel />

          <div className="mt-3 flex items-center justify-between">
            <BackButton href="/start" />
            <LinkButton href="/mandate" variant="primary">
              continue
            </LinkButton>
          </div>
        </div>
      </ScreenShell>
    </SessionGate>
  );
}
