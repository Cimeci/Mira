"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useFlow } from "@/lib/flow-context";
import { ScreenTitle } from "@/components/ui/ScreenTitle";
import { BackButton } from "@/components/ui/BackButton";
import { FaceScanCard } from "./FaceScanCard";
import { FaceScanModal } from "./FaceScanModal";
import { useFaceScan } from "./useFaceScan";

export function SignatureFlow() {
  const router = useRouter();
  const { mandateSigned } = useFlow();
  const scan = useFaceScan(() => router.push("/case"));

  // gate: the facial signature requires a signed mandate (mirrors goTo(4))
  useEffect(() => {
    if (!mandateSigned) router.replace("/mandate");
  }, [mandateSigned, router]);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-[10px] text-caption tracking-[0.06em] text-mira-muted-dim">
        <span className="inline-flex h-4 w-4 flex-shrink-0 -rotate-6 items-center justify-center border border-[rgba(181,107,255,0.5)] text-[9px] text-mira-electric-lilac">
          ✓
        </span>
        <span>mandate signed ✓ · case mira-4821</span>
      </div>

      <div>
        <ScreenTitle>create your facial signature</ScreenTitle>
        <p className="mt-[10px] max-w-[660px] text-[14px] leading-[1.6] text-mira-muted-text">
          mira needs one live picture to recognize possible matches and verify
          evidence. no identity document is required.
        </p>
      </div>

      <FaceScanCard onScan={(el) => scan.open(el)} />

      <BackButton href="/mandate" className="self-start" />

      <FaceScanModal scan={scan} />
    </div>
  );
}
