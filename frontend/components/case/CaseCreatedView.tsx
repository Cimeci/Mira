"use client";

import { useEffect, useRef, useState } from "react";
import { useFlow } from "@/lib/flow-context";
import { dispatchScout } from "@/lib/api";
import { CaseStatusView } from "./CaseStatusView";

/**
 * The "your case is open" screen at the END of intake. Opening the case is what
 * dispatches the Computer Use scout — never earlier (consent-first, G-1: the mandate
 * is already signed by the time we land here, gated by SignatureFlow). It fires once
 * on mount for the URL collected during intake; the dashboard detail route reuses the
 * plain CaseStatusView and does NOT re-dispatch.
 */
export function CaseCreatedView() {
  const { urls } = useFlow();
  const firstUrl = urls.map((u) => u.trim()).find(Boolean) ?? "";
  const dispatched = useRef(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fire exactly once — the case opens once. The ref also guards against React
    // StrictMode's double-invoked effects in dev (would otherwise open two cases).
    if (dispatched.current || !firstUrl) return;
    dispatched.current = true;
    dispatchScout(firstUrl).catch((e) =>
      setError(e instanceof Error ? e.message : String(e))
    );
  }, [firstUrl]);

  return (
    <>
      <CaseStatusView targetLabel={firstUrl || "[url]"} />
      {error && (
        <p role="alert" className="mx-auto max-w-[860px] px-6 text-body-sm text-mira-muted-text">
          scout dispatch failed: {error}
        </p>
      )}
    </>
  );
}
