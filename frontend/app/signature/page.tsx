import { ScreenShell } from "@/components/layout/ScreenShell";
import { SessionGate } from "@/components/auth/SessionGate";
import { SignatureFlow } from "@/components/signature/SignatureFlow";

export default function FacialSignatureScreen() {
  return (
    <SessionGate>
      <ScreenShell
        progress={{ label: "facial signature", filled: 4 }}
        contentWidth={880}
        footer="private by design. no identity document required."
      >
        <SignatureFlow />
      </ScreenShell>
    </SessionGate>
  );
}
