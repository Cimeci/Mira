"use client";

import { useCallback, useEffect, useState } from "react";
import { ScreenShell } from "@/components/layout/ScreenShell";
import { ScreenTitle } from "@/components/ui/ScreenTitle";
import { LinkButton } from "@/components/ui/LinkButton";
import { Button } from "@/components/ui/Button";
import { CaseCard } from "./CaseCard";
import { CaseTimeline } from "./CaseTimeline";
import { useEventSource, type SSEEvent } from "@/lib/useEventSource";
import { isGateOpen, statusLabel, targetLabel, timelineFor } from "@/lib/caseProgress";

const FOOTER = "mira is handling it — you stay in control of every legal step.";

interface StageEventPayload {
  to_status?: string;
  payload?: { url?: string };
}

type Phase = "loading" | "notfound" | "ready";

/**
 * Live case detail. Reads the current snapshot once (to detect a missing case
 * and paint immediately), then follows the pipeline over SSE: each stage
 * transition advances the timeline, and when mira reaches the G-7 gate the
 * prepared DSA notice is shown with approve/hold — nothing is sent until the
 * victim decides. Replaces the old static, mock-driven detail view.
 */
export function CaseDetailLive({ caseId, apiBase }: { caseId: string; apiBase: string }) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [status, setStatus] = useState<string | null>(null);
  const [target, setTarget] = useState<string>("");
  const [notice, setNotice] = useState<{ url: string; text: string } | null>(null);
  const [finished, setFinished] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${apiBase}/cases/${caseId}`, { cache: "no-store" });
        if (res.status === 404) {
          if (!cancelled) setPhase("notfound");
          return;
        }
        if (!res.ok) throw new Error(`status ${res.status}`);
        const d = (await res.json()) as {
          current_status?: string | null;
          pending_notice?: { url: string; text: string } | null;
          finished?: boolean;
        };
        if (cancelled) return;
        setStatus(d.current_status ?? null);
        setNotice(d.pending_notice ?? null);
        setFinished(Boolean(d.finished));
        setPhase("ready");
      } catch {
        // A dead backend must not leave a blank screen: surface it, still stream.
        if (!cancelled) {
          setError("mira api unreachable — is the backend running?");
          setPhase("ready");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiBase, caseId]);

  const onMessage = useCallback((msg: SSEEvent) => {
    if (msg.kind === "stage" && msg.event) {
      const ev = msg.event as StageEventPayload;
      if (ev.to_status) setStatus(ev.to_status);
      if (ev.payload?.url) setTarget(ev.payload.url);
    } else if (msg.kind === "notice") {
      setNotice({ url: msg.url ?? "", text: msg.text ?? "" });
    } else if (msg.kind === "done") {
      setFinished(true);
    } else if (msg.kind === "error") {
      setError(msg.message ?? "pipeline error");
    }
  }, []);

  // Stream only once the case is known to exist — otherwise a 404 would trigger
  // the hook's reconnect loop against a case that will never appear.
  useEventSource({
    url: `${apiBase}/cases/${caseId}/events`,
    enabled: phase === "ready",
    onMessage,
  });

  const decide = useCallback(
    async (approved: boolean) => {
      setConfirming(true);
      try {
        const res = await fetch(`${apiBase}/cases/${caseId}/confirm`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ approved, url: notice?.url }),
        });
        if (!res.ok) throw new Error(`status ${res.status}`);
        // On success the pipeline resumes; the SSE stream carries it forward and
        // the gate panel closes as the status leaves AWAITING_CONFIRM.
      } catch {
        setError("couldn't send your decision — try again");
        setConfirming(false);
      }
    },
    [apiBase, caseId, notice]
  );

  if (phase === "loading") {
    return (
      <ScreenShell contentWidth={860} centered footer={FOOTER}>
        <p className="text-[15px] text-mira-muted-text">loading case…</p>
      </ScreenShell>
    );
  }

  if (phase === "notfound") {
    return (
      <ScreenShell contentWidth={860} centered footer={FOOTER}>
        <div className="flex flex-col items-center gap-6 text-center">
          <ScreenTitle>case not found</ScreenTitle>
          <p className="text-[15px] text-mira-muted-text">
            this case isn&rsquo;t in the current session.
          </p>
          <LinkButton href="/cases" variant="primary" className="px-9">
            back to all cases
          </LinkButton>
        </div>
      </ScreenShell>
    );
  }

  const gateOpen = isGateOpen(status) && Boolean(notice);
  const steps = timelineFor(status);

  return (
    <ScreenShell contentWidth={860} footer={FOOTER}>
      <div className="flex flex-col gap-14 md:flex-row md:items-start">
        <div className="flex w-full flex-col gap-[22px] md:w-[420px] md:flex-shrink-0">
          <ScreenTitle>{finished ? "case complete ✓" : "your case is live"}</ScreenTitle>

          <CaseCard
            caseId={caseId}
            targetLabel={targetLabel(target)}
            status={statusLabel(status)}
          />

          {error && <p className="text-caption text-mira-danger">{error}</p>}

          {gateOpen && (
            <div className="flex flex-col gap-4 rounded-chip border border-[rgba(255,198,92,0.5)] bg-[rgba(255,198,92,0.08)] p-5">
              <div className="text-label uppercase tracking-label text-mira-warn">
                your approval needed — G-7
              </div>
              <p className="text-[14px] leading-[1.5] text-mira-muted-text">
                mira prepared this DSA notice. nothing is sent until you approve.
              </p>
              <pre className="max-h-52 overflow-auto whitespace-pre-wrap rounded-card border border-[rgba(181,107,255,0.25)] bg-mira-night p-4 text-[12px] leading-[1.5] text-mira-muted-text">
                {notice?.text}
              </pre>
              <div className="flex flex-wrap items-center gap-[14px]">
                <Button
                  variant="flow"
                  size="lg"
                  className="px-7"
                  disabled={confirming}
                  onClick={() => decide(true)}
                >
                  {confirming ? "sending…" : "approve & send"}
                </Button>
                <Button
                  variant="ghost"
                  size="md"
                  disabled={confirming}
                  onClick={() => decide(false)}
                >
                  hold
                </Button>
              </div>
            </div>
          )}

          <LinkButton href="/cases" variant="ghost" size="md">
            back to all cases
          </LinkButton>
        </div>

        <CaseTimeline steps={steps} />
      </div>
    </ScreenShell>
  );
}
