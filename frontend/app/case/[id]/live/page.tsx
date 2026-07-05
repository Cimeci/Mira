import { ScreenShell } from "@/components/layout/ScreenShell";
import { ScreenTitle } from "@/components/ui/ScreenTitle";
import { BackButton } from "@/components/ui/BackButton";
import { LiveAgentView } from "@/components/case/LiveAgentView";

interface CaseLivePageProps {
  params: { id: string };
}

export default function CaseLiveScreen({ params }: CaseLivePageProps) {
  const { id } = params;
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "";

  return (
    <ScreenShell
      contentWidth={1280}
      footer="mira is handling it — you never have to look again."
    >
      <div className="flex flex-col gap-[22px]">
        <div className="flex items-center justify-between gap-4">
          <div className="flex flex-col gap-1">
            <ScreenTitle>live agent view</ScreenTitle>
            <span className="font-mono text-caption text-mira-muted-dim">{id}</span>
          </div>
          <BackButton href="/dashboard" />
        </div>

        <LiveAgentView caseId={id} apiBase={apiBase} />
      </div>
    </ScreenShell>
  );
}
