import { ScreenShell } from "@/components/layout/ScreenShell";
import { MandateSigning } from "@/components/mandate/MandateSigning";

export default function MandateScreen() {
  return (
    <ScreenShell
      progress={{ label: "mandate", filled: 3 }}
      contentWidth={1080}
      footer="you can revoke this mandate and delete your data at any time."
    >
      <MandateSigning />
    </ScreenShell>
  );
}
