import { ScreenShell } from "@/components/layout/ScreenShell";
import { SessionGate } from "@/components/auth/SessionGate";
import { ScreenTitle } from "@/components/ui/ScreenTitle";
import { FieldLabel } from "@/components/ui/FieldLabel";
import { Textarea } from "@/components/ui/Textarea";
import { LinkButton } from "@/components/ui/LinkButton";
import { BackButton } from "@/components/ui/BackButton";
import { UrlList } from "@/components/start/UrlList";
import { DiscoveryChips } from "@/components/start/DiscoveryChips";

export default function StartCaseScreen() {
  return (
    <SessionGate>
      <ScreenShell
        progress={{ label: "start your case", filled: 1 }}
        contentWidth={720}
        centered
        footer="we only ask for the minimum needed to open your case."
      >
        <div className="flex flex-col gap-[26px]">
          <ScreenTitle>start your case</ScreenTitle>

          <div className="flex flex-col gap-2">
            <FieldLabel htmlFor="what-happened">what happened?</FieldLabel>
            <Textarea
              id="what-happened"
              placeholder="i found my image on this website and i want it taken down…"
            />
          </div>

          <div className="flex flex-col gap-2">
            <FieldLabel>where did you find it?</FieldLabel>
            <UrlList />
          </div>

          <div className="flex flex-col gap-[10px]">
            <FieldLabel>how did you discover it?</FieldLabel>
            <DiscoveryChips />
          </div>

          <div className="mt-3 flex items-center justify-between">
            <BackButton href="/" />
            <LinkButton href="/actions" variant="primary">
              continue
            </LinkButton>
          </div>
        </div>
      </ScreenShell>
    </SessionGate>
  );
}
