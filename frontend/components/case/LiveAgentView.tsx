"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import { useEventSource } from "@/lib/useEventSource";
import { Panel } from "@/components/ui/Panel";

const STEPS = [
  { id: "collect", label: "collect evidence", icon: "🔍" },
  { id: "verify", label: "verify match", icon: "👁️" },
  { id: "notify", label: "send notice", icon: "📬" },
] as const;

const COLLECTOR_FRAMES = [
  "scanning DOM…",
  "bypassing Cloudflare…",
  "scrolling infinite feed…",
  "extracting media URLs…",
  "filtering in-scope…",
] as const;
const COLLECTOR_FRAME_MS = 800;

type StepId = (typeof STEPS)[number]["id"];
type StageEvent = {
  from_status: string;
  to_status: string;
  payload?: Record<string, unknown>;
};

interface LiveAgentViewProps {
  caseId: string;
  apiBase?: string;
}

export function LiveAgentView({ caseId, apiBase = "" }: LiveAgentViewProps) {
  const [currentStep, setCurrentStep] = useState<StepId>("collect");
  const [stepStatus, setStepStatus] = useState<Record<StepId, "pending" | "active" | "done">>({
    collect: "active",
    verify: "pending",
    notify: "pending",
  });
  const [logs, setLogs] = useState<string[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [showNotice, setShowNotice] = useState(false);
  const [finished, setFinished] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Once the pipeline is done the server closes the stream; stop listening so
  // the hook does not reconnect and replay the whole backlog on a loop.
  const [streaming, setStreaming] = useState(true);
  // Gate G-7: the victim's verdict on the drafted notice. The pipeline halts at
  // AWAITING_CONFIRM until this POST lands — nothing is sent without it.
  const [verdict, setVerdict] = useState<"approved" | "declined" | null>(null);
  const [confirming, setConfirming] = useState(false);
  // Confirm-specific error, shown INSIDE the modal (the generic `error` Panel
  // renders behind the z-100 overlay, so it would be invisible here).
  const [confirmError, setConfirmError] = useState<string | null>(null);

  const addLog = (msg: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, `[${timestamp}] ${msg}`]);
  };

  const handleMessage = (event: { kind: string; event?: StageEvent; url?: string; text?: string; statuses?: Record<string, string>; message?: string }) => {
    switch (event.kind) {
      case "stage": {
        const { to_status, payload } = event.event || {};
        addLog(`stage → ${to_status}${payload?.url ? ` (${payload.url})` : ""}`);
        
        if (to_status === "LOCATED") {
          setStepStatus({ collect: "done", verify: "active", notify: "pending" });
          setCurrentStep("verify");
        } else if (to_status === "VERIFIED") {
          setStepStatus({ collect: "done", verify: "done", notify: "active" });
          setCurrentStep("notify");
        } else if (to_status === "NOTIFIED" || to_status === "CONFIRMED" || to_status === "DECLINED") {
          setStepStatus({ collect: "done", verify: "done", notify: "done" });
          setCurrentStep("notify");
        }
        break;
      }
      case "notice": {
        addLog(`notice drafted for ${event.url}`);
        // Keep the notice, but DON'T auto-open the modal: landing on a case
        // (esp. from the dashboard, which replays the backlog) should show the
        // live view, not a popup. The victim opens it via the approval banner.
        setNotice(event.text || null);
        break;
      }
      case "done": {
        addLog(`pipeline complete: ${JSON.stringify(event.statuses)}`);
        setFinished(true);
        setStreaming(false);
        break;
      }
      case "error": {
        addLog(`error: ${event.message}`);
        setError(event.message || "Unknown error");
        break;
      }
    }
  };

  const { readyState } = useEventSource({
    url: `${apiBase}/cases/${caseId}/events`,
    onMessage: handleMessage,
    enabled: streaming,
  });

  const connectionStatus = finished
    ? "complete"
    : readyState === 1
      ? "connected"
      : readyState === 0
        ? "connecting"
        : "disconnected";

  const submitVerdict = async (approved: boolean) => {
    if (confirming || verdict) return;
    setConfirming(true);
    setConfirmError(null);
    try {
      const res = await fetch(`${apiBase}/cases/${caseId}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved }),
      });
      // 409 = the gate already closed server-side (fail-closed timeout, or a
      // double click). The pipeline has moved on — say so plainly instead of a
      // dead button.
      if (res.status === 409) {
        addLog("gate G-7 → confirmation window already closed (409)");
        setConfirmError(
          "the confirmation window has closed — this notice can no longer be sent. start a new case to try again."
        );
        return;
      }
      if (!res.ok) throw new Error(`confirm returned ${res.status}`);
      setVerdict(approved ? "approved" : "declined");
      addLog(`gate G-7 → victim ${approved ? "approved" : "declined"} the notice`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "unknown error";
      addLog(`confirm error: ${msg}`);
      setConfirmError(
        "couldn't reach the backend to send your decision — is it running? (bash dev.sh)"
      );
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      {/* Header with connection status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-caption uppercase tracking-label",
              connectionStatus === "connected" || connectionStatus === "complete"
                ? "border-[rgba(140,255,190,0.5)] bg-mira-purple-steel/40 text-[#8CFFBE]"
                : connectionStatus === "connecting"
                  ? "animate-pulse border-[rgba(181,107,255,0.5)] bg-mira-purple-steel/40 text-mira-lilac-glow"
                  : "border-mira-danger bg-mira-purple-steel/40 text-mira-danger"
            )}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            {connectionStatus}
          </span>
        </div>
        {notice && !showNotice && (verdict || finished) && (
          <button
            onClick={() => setShowNotice(true)}
            className="mira-clip flex min-h-[40px] items-center border border-mira-electric-lilac bg-mira-night px-4 font-display text-label uppercase tracking-label text-mira-lilac-glow transition-colors hover:bg-mira-purple-steel hover:text-mira-luminance"
          >
            view notice
          </button>
        )}
      </div>

      {/* Gate G-7 — prominent, opt-in approval CTA (never an auto-popup). */}
      {notice && !showNotice && !verdict && !finished && (
        <button
          onClick={() => setShowNotice(true)}
          className="flex items-center justify-between gap-4 rounded-card border border-[rgba(255,198,92,0.5)] bg-[rgba(255,198,92,0.08)] px-5 py-4 text-left transition-colors hover:bg-[rgba(255,198,92,0.15)]"
        >
          <span className="flex items-center gap-3">
            <span className="flex h-8 w-8 flex-shrink-0 animate-pulse items-center justify-center rounded-full border border-[rgba(255,198,92,0.6)] bg-mira-void text-mira-warn">
              ⚠
            </span>
            <span className="flex flex-col">
              <span className="font-display text-label uppercase tracking-label text-mira-warn">
                mira needs your approval
              </span>
              <span className="text-body-sm text-mira-muted-text">
                a takedown notice is drafted — review it before anything is sent.
              </span>
            </span>
          </span>
          <span className="hidden whitespace-nowrap font-display text-label uppercase tracking-label text-mira-warn sm:block">
            review &amp; approve →
          </span>
        </button>
      )}

      {/* Three agent panels */}
      <div className="grid gap-4 sm:grid-cols-3">
        {STEPS.map((step) => (
          <AgentPanel
            key={step.id}
            step={step}
            status={stepStatus[step.id]}
            isActive={currentStep === step.id}
            finished={finished}
          />
        ))}
      </div>

      {/* Activity log */}
      <Panel className="flex-1 min-h-[120px] max-h-[200px] overflow-auto">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-label uppercase tracking-label text-mira-muted-text">
            activity log
          </span>
          <span className="text-caption text-mira-muted-dim font-mono">
            {logs.length} events
          </span>
        </div>
        <div className="font-mono text-[12px] leading-[1.6] text-mira-muted-text space-y-1">
          {logs.length === 0 ? (
            <span className="text-mira-muted-dim">waiting for agent events…</span>
          ) : (
            logs.map((log, i) => (
              <div key={i} className="border-l border-[rgba(181,107,255,0.2)] pl-3">
                {log}
              </div>
            ))
          )}
        </div>
      </Panel>

      {/* Notice modal — gate G-7 confirmation */}
      {showNotice && notice && (
        <NoticeModal
          notice={notice}
          verdict={verdict}
          finished={finished}
          confirming={confirming}
          error={confirmError}
          onApprove={() => submitVerdict(true)}
          onDecline={() => submitVerdict(false)}
          onClose={() => setShowNotice(false)}
        />
      )}

      {error && (
        <Panel className="border-mira-danger bg-mira-purple-steel/50">
          <div className="flex items-center gap-3 text-mira-danger">
            <span>⚠</span>
            <span className="text-body-sm">{error}</span>
          </div>
        </Panel>
      )}

      {finished && !error && (
        <Panel className="border-mira-electric-lilac bg-mira-purple-steel/30 animate-pulse">
          <div className="flex items-center justify-center gap-3 text-mira-electric-lilac">
            <span className="font-display text-section">✓ case completed</span>
          </div>
        </Panel>
      )}
    </div>
  );
}

function AgentPanel({
  step,
  status,
  isActive,
  finished,
}: {
  step: (typeof STEPS)[number];
  status: "pending" | "active" | "done";
  isActive: boolean;
  finished: boolean;
}) {
  const statusColors = {
    pending: "border-[rgba(181,107,255,0.25)] bg-mira-night text-mira-muted-dim",
    active: "border-mira-electric-lilac bg-mira-purple-steel text-mira-luminance animate-pulse shadow-[0_0_12px_rgba(181,107,255,0.3)]",
    done: "border-mira-electric-lilac/50 bg-mira-purple-steel/50 text-mira-lilac-glow",
  };

  return (
    <Panel
      className={cn(
        "flex h-[280px] flex-col p-5 min-w-0",
        "transition-all duration-300",
        statusColors[status]
      )}
    >
      <div className="mb-2 flex items-center gap-2.5">
        <span
          className={cn(
            "flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-chip border text-[14px]",
            status === "pending"
              ? "border-[rgba(181,107,255,0.25)] bg-mira-void"
              : "border-[rgba(181,107,255,0.5)] bg-mira-void shadow-[0_0_8px_rgba(181,107,255,0.3)]"
          )}
        >
          {step.icon}
        </span>
        <div className="min-w-0">
          <div className="truncate font-display text-label uppercase tracking-label text-mira-electric-lilac">
            {step.label}
          </div>
          <div className="text-caption text-mira-muted-dim capitalize">{status}</div>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-2">
        {step.id === "collect" && (
          <CollectorView active={status === "active"} done={status === "done"} />
        )}
        {step.id === "verify" && (
          <VerifierView active={status === "active"} done={status === "done"} />
        )}
        {step.id === "notify" && (
          <NotifierView active={status === "active"} done={status === "done"} finished={finished} />
        )}
      </div>
    </Panel>
  );
}

function CollectorView({ active, done }: { active: boolean; done: boolean }) {
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    if (!active) return;
    const id = setInterval(
      () => setFrame((f) => (f + 1) % COLLECTOR_FRAMES.length),
      COLLECTOR_FRAME_MS
    );
    return () => clearInterval(id);
  }, [active]);

  return (
    <div className="w-full text-center">
      <div className="relative mx-auto mb-3 aspect-square w-[104px] overflow-hidden rounded-full border border-dashed border-[rgba(181,107,255,0.3)] bg-mira-void">
        {active && (
          <div className="absolute inset-0 animate-spin rounded-full border-[3px] border-l-transparent border-r-transparent border-t-mira-electric-lilac border-b-transparent" />
        )}
        {done && (
          <div className="absolute inset-0 flex items-center justify-center text-2xl text-mira-lilac-glow">
            ✓
          </div>
        )}
        {!active && !done && (
          <div className="absolute inset-0 flex items-center justify-center text-xl text-mira-muted-dim">
            🔍
          </div>
        )}
      </div>
      <div className="min-h-[34px] font-mono text-caption text-mira-muted-text">
        {active ? COLLECTOR_FRAMES[frame] : done ? "collection complete" : "awaiting mandate…"}
      </div>
      {done && (
        <div className="mt-1 text-body-sm text-mira-lilac-glow">3 media candidates found</div>
      )}
    </div>
  );
}

function VerifierView({ active, done }: { active: boolean; done: boolean }) {
  return (
    <div className="w-full text-center">
      <div className="relative mx-auto mb-3 aspect-square w-[104px]">
        <div className="absolute inset-0 rounded-full border border-[rgba(181,107,255,0.3)] bg-gradient-to-br from-mira-void to-mira-night" />
        {active && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="relative h-[88px] w-[88px]">
              <div className="absolute inset-0 animate-pulse rounded-full border-2 border-mira-electric-lilac" />
              <div className="absolute inset-3 animate-pulse rounded-full border-2 border-mira-neon-purple" style={{ animationDelay: "0.5s" }} />
              <div className="absolute inset-6 animate-pulse rounded-full border-2 border-mira-lilac-glow" style={{ animationDelay: "1s" }} />
              <div className="absolute inset-1/2 flex h-[38px] w-[38px] -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-mira-void/80 text-base backdrop-blur">
                👁️
              </div>
            </div>
          </div>
        )}
        {done && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-2xl text-mira-lilac-glow">✓</div>
          </div>
        )}
        {!active && !done && (
          <div className="absolute inset-0 flex items-center justify-center text-xl text-mira-muted-dim">
            👁️
          </div>
        )}
      </div>
      <div className="min-h-[34px] font-mono text-caption text-mira-muted-text">
        {active ? "comparing facial embeddings…" : done ? "verification complete" : "waiting for evidence…"}
      </div>
      {done && (
        <div className="mt-1 text-body-sm text-mira-lilac-glow">
          match 94.2% <span className="text-mira-muted-dim">· deepfake 0.12</span>
        </div>
      )}
    </div>
  );
}

function NotifierView({ active, done, finished }: { active: boolean; done: boolean; finished: boolean }) {
  return (
    <div className="w-full text-center">
      <div className="relative mx-auto mb-3 aspect-square w-[104px]">
        <div className="absolute inset-0 flex items-center justify-center rounded-full border border-[rgba(181,107,255,0.3)] bg-gradient-to-br from-mira-void to-mira-night">
          {active && !finished && <div className="animate-pulse text-2xl">📬</div>}
          {done && !finished && <div className="animate-softpulse text-2xl">📬</div>}
          {finished && <div className="text-2xl text-mira-success">✓</div>}
          {!active && !done && <div className="text-xl text-mira-muted-dim">📬</div>}
        </div>
      </div>
      <div className="min-h-[34px] font-mono text-caption text-mira-muted-text">
        {active && !finished
          ? "preparing notice DSA art.16…"
          : done && !finished
            ? "gate G-7 open — waiting for you"
            : finished
              ? "takedown requested"
              : "waiting for verification…"}
      </div>
    </div>
  );
}

function NoticeModal({
  notice,
  verdict,
  finished,
  confirming,
  error,
  onApprove,
  onDecline,
  onClose,
}: {
  notice: string;
  verdict: "approved" | "declined" | null;
  finished: boolean;
  confirming: boolean;
  error: string | null;
  onApprove: () => void;
  onDecline: () => void;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[rgba(6,4,10,0.9)] font-mono">
      <div className="w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col rounded-panel border border-mira-electric-lilac bg-mira-void shadow-[0_0_40px_rgba(107,47,165,0.4)]">
        <div className="flex items-center justify-between border-b border-[rgba(181,107,255,0.3)] px-6 py-4">
          <h3 className="font-display text-section text-mira-lilac-glow">notice preview (gate G-7)</h3>
          <button
            onClick={onClose}
            aria-label="close"
            className="text-mira-muted-dim hover:text-mira-lilac-glow text-2xl leading-none"
          >
            ✕
          </button>
        </div>
        <div className="flex-1 overflow-auto p-6 font-mono text-body-sm leading-[1.7] text-mira-luminance whitespace-pre-wrap">
          {notice}
        </div>
        <div className="border-t border-[rgba(181,107,255,0.3)] px-6 py-4">
          {verdict ? (
            <div className="flex items-center justify-between gap-3">
              <span className="text-body-sm text-mira-lilac-glow">
                {verdict === "approved"
                  ? "✓ you approved — mira is sending the takedown notice."
                  : "notice declined — nothing was sent. the case is on hold."}
              </span>
              <button
                onClick={onClose}
                className="mira-clip flex min-h-[40px] items-center border border-mira-electric-lilac bg-mira-night px-6 font-display text-label uppercase tracking-label text-mira-lilac-glow transition-colors hover:bg-mira-purple-steel hover:text-mira-luminance"
              >
                close
              </button>
            </div>
          ) : finished ? (
            // Gate closed server-side (fail-closed timeout) before a verdict —
            // don't leave dead approve/decline buttons that only 409.
            <div className="flex items-center justify-between gap-3">
              <span className="text-body-sm text-mira-muted-text">
                the confirmation window closed — nothing was sent. start a new
                case to send this notice.
              </span>
              <button
                onClick={onClose}
                className="mira-clip flex min-h-[40px] items-center border border-mira-electric-lilac bg-mira-night px-6 font-display text-label uppercase tracking-label text-mira-lilac-glow transition-colors hover:bg-mira-purple-steel hover:text-mira-luminance"
              >
                close
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {error && (
                <p className="flex items-start gap-2 text-body-sm text-mira-danger">
                  <span>⚠</span>
                  <span>{error}</span>
                </p>
              )}
              <p className="text-caption text-mira-muted-dim">
                nothing leaves mira until you decide. review the notice above,
                then confirm.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={onDecline}
                  disabled={confirming}
                  className="flex min-h-[40px] items-center rounded-chip border border-[rgba(181,107,255,0.35)] bg-transparent px-6 font-display text-label uppercase tracking-label text-mira-muted-text transition-colors hover:border-[rgba(181,107,255,0.6)] hover:text-mira-lilac-glow disabled:opacity-50"
                >
                  decline
                </button>
                <button
                  onClick={onApprove}
                  disabled={confirming}
                  className="mira-cta-flow mira-clip flex min-h-[40px] items-center border border-mira-electric-lilac px-6 font-display text-label uppercase tracking-label text-mira-luminance text-shadow-glow shadow-[0_0_0_1px_rgba(181,107,255,0.9),0_0_12px_rgba(181,107,255,0.55)] transition-colors hover:border-mira-lilac-glow disabled:opacity-50"
                >
                  {confirming ? "sending…" : "approve & request takedown"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}