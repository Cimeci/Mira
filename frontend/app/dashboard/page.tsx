import { ScreenShell } from "@/components/layout/ScreenShell";
import { CaseBoard } from "@/components/case/CaseBoard";

export default function DashboardScreen() {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "";

  return (
    <ScreenShell
      contentWidth={1120}
      footer="mira watches every case — you stay in control of every step."
    >
      <CaseBoard apiBase={apiBase} />
    </ScreenShell>
  );
}
