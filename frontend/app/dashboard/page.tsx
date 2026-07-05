import { ScreenShell } from "@/components/layout/ScreenShell";
import { SessionGate } from "@/components/auth/SessionGate";
import { CaseBoard } from "@/components/case/CaseBoard";

export default function DashboardScreen() {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "";

  return (
    <SessionGate>
      <ScreenShell
        contentWidth={1120}
        homeHref="/dashboard"
        footer="mira watches every case — you stay in control of every step."
      >
        <CaseBoard apiBase={apiBase} />
      </ScreenShell>
    </SessionGate>
  );
}
