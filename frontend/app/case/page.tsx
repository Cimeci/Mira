import { ScreenShell } from "@/components/layout/ScreenShell";
import { CaseTimeline } from "@/components/case/CaseTimeline";
import { CaseOpenPanel } from "@/components/case/CaseOpenPanel";

export default function CaseCreatedScreen() {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "";

  return (
    <ScreenShell
      progress={{ label: "case open", filled: 5 }}
      contentWidth={860}
      footer="mira is handling it — you never have to look again."
    >
      <div className="flex flex-col gap-14 md:flex-row md:items-start">
        <CaseOpenPanel apiBase={apiBase} />
        <CaseTimeline />
      </div>
    </ScreenShell>
  );
}
