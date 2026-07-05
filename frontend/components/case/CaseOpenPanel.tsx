"use client";

import { useEffect, useRef, useState } from "react";
import { useFlow } from "@/lib/flow-context";
import { ScreenTitle } from "@/components/ui/ScreenTitle";
import { LinkButton } from "@/components/ui/LinkButton";
import { BackButton } from "@/components/ui/BackButton";
import { Button } from "@/components/ui/Button";
import { CaseCard } from "./CaseCard";

type CreateState = "creating" | "ready" | "error";

/**
 * Turns the narrative "your case is open" screen into a real case: it POSTs to
 * the backend once (guarded against StrictMode double-invoke and back-nav via
 * the flow context), so the case shows up on the dashboard and gets a live view.
 */
export function CaseOpenPanel({ apiBase }: { apiBase: string }) {
  const { caseId, setCaseId } = useFlow();
  const [state, setState] = useState<CreateState>(caseId ? "ready" : "creating");
  const started = useRef(false);

  useEffect(() => {
    if (caseId) {
      setState("ready");
      return;
    }
    if (started.current) return;
    started.current = true;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    (async () => {
      try {
        const res = await fetch(`${apiBase}/cases`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}",
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`status ${res.status}`);
        const data = (await res.json()) as { case_id: string };
        setCaseId(data.case_id);
        setState("ready");
      } catch {
        setState("error");
      } finally {
        clearTimeout(timer);
      }
    })();
  }, [apiBase, caseId, setCaseId]);

  const cardId =
    state === "ready" ? caseId : state === "error" ? "—" : "opening…";
  const cardStatus =
    state === "ready"
      ? "evidence collection started"
      : state === "error"
        ? "mira api unreachable"
        : "opening your case…";

  return (
    <div className="flex w-full flex-col gap-[22px] md:w-[400px] md:flex-shrink-0">
      <ScreenTitle>your case is open ✓</ScreenTitle>

      <CaseCard
        caseId={cardId}
        targetUrl="mock-host.local/media/xyz789"
        status={cardStatus}
      />

      <p className="text-[14px] leading-[1.5] text-mira-muted-text">
        our scout is now collecting and verifying evidence. we&rsquo;ll notify
        you before any step that needs your approval.
      </p>

      <div className="flex flex-wrap items-center gap-[14px]">
        <BackButton href="/signature" />
        {state === "ready" ? (
          <LinkButton
            href={`/case/${caseId}/live`}
            variant="flow"
            className="px-7"
          >
            watch mira work live
          </LinkButton>
        ) : (
          <Button variant="flow" size="lg" className="px-7" disabled>
            {state === "error" ? "unavailable" : "opening…"}
          </Button>
        )}
        <LinkButton href="/dashboard" variant="ghost" size="md">
          all cases
        </LinkButton>
      </div>

      {state === "error" && (
        <p className="text-caption text-mira-danger">
          couldn&rsquo;t open a live case — is the backend running? start it with
          <span className="font-mono"> bash dev.sh</span>, then reload.
        </p>
      )}
    </div>
  );
}
