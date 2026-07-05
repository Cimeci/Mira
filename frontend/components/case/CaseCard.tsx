import { cn } from "@/lib/cn";
import { caseStatusView, relativeTime, type CaseTone } from "@/lib/caseStatus";

interface CaseCardProps {
  caseId: string;
  targetUrl: string;
  /** Raw pipeline status (mira.types.Status), or null while starting. */
  status: string | null;
  createdAt?: string | null;
  /** Show the "open →" affordance — only when the card is a clickable link. */
  interactive?: boolean;
}

const TONE: Record<CaseTone, { pill: string; dot: string; bar: string }> = {
  active: {
    pill: "border-[rgba(181,107,255,0.5)] bg-mira-purple-steel text-mira-lilac-glow",
    dot: "bg-mira-electric-lilac shadow-[0_0_8px_rgba(181,107,255,0.85)]",
    bar: "bg-mira-electric-lilac shadow-[0_0_8px_rgba(181,107,255,0.6)]",
  },
  action: {
    pill: "border-[rgba(255,198,92,0.5)] bg-[rgba(255,198,92,0.12)] text-mira-warn",
    dot: "bg-mira-warn shadow-[0_0_8px_rgba(255,198,92,0.8)]",
    bar: "bg-mira-warn shadow-[0_0_8px_rgba(255,198,92,0.55)]",
  },
  done: {
    pill: "border-[rgba(140,255,190,0.45)] bg-[rgba(140,255,190,0.1)] text-mira-success",
    dot: "bg-mira-success shadow-[0_0_8px_rgba(140,255,190,0.7)]",
    bar: "bg-mira-success shadow-[0_0_8px_rgba(140,255,190,0.5)]",
  },
  halted: {
    pill: "border-[rgba(255,92,138,0.45)] bg-[rgba(255,92,138,0.1)] text-mira-danger",
    dot: "bg-mira-danger shadow-[0_0_8px_rgba(255,92,138,0.7)]",
    bar: "bg-mira-danger",
  },
};

const STAGES = ["collect", "verify", "notify"] as const;

/**
 * Case summary card: status pill (colored by state), case id, target, and the
 * collect→verify→notify stage tracker. Meant to sit inside a `group` link so
 * hover lifts the whole card and reveals the "open" affordance.
 */
export function CaseCard({
  caseId,
  targetUrl,
  status,
  createdAt,
  interactive = true,
}: CaseCardProps) {
  const view = caseStatusView(status);
  const tone = TONE[view.tone];
  const time = relativeTime(createdAt ?? null);
  const isLive = view.tone === "active" || view.tone === "action";

  return (
    <div className="flex h-full flex-col justify-between gap-5 rounded-card border border-[rgba(181,107,255,0.3)] bg-mira-night p-5 shadow-[0_0_14px_rgba(107,47,165,0.12)] transition-all duration-200 group-hover:border-[rgba(181,107,255,0.65)] group-hover:shadow-card">
      <div className="flex items-center justify-between gap-3">
        <span
          className={cn(
            "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-caption uppercase tracking-label",
            tone.pill,
            view.needsAction && "animate-pulse"
          )}
        >
          <span className={cn("h-1.5 w-1.5 rounded-full", tone.dot, isLive && "animate-pulse")} />
          {view.label}
        </span>
        {time && <span className="text-caption text-mira-muted-dim">{time}</span>}
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="font-display text-[15px] tracking-[0.02em] text-mira-lilac-glow">
          {caseId}
        </div>
        <div className="flex items-center gap-2 text-body-sm text-mira-muted-text">
          <span className="text-mira-muted-dim">⟐</span>
          <span className="min-w-0 flex-1 truncate">{targetUrl}</span>
        </div>
      </div>

      <div className="flex items-end justify-between gap-4">
        <div className="flex flex-1 flex-col gap-2">
          <div className="flex gap-1.5">
            {STAGES.map((_, i) => {
              const filled = i < view.stage;
              const activeStage = i === view.stage && isLive;
              return (
                <div
                  key={i}
                  className={cn(
                    "h-1 flex-1 rounded-full",
                    filled
                      ? tone.bar
                      : activeStage
                        ? cn(tone.bar, "animate-pulse opacity-90")
                        : "bg-[rgba(181,107,255,0.15)]"
                  )}
                />
              );
            })}
          </div>
          <div className="flex justify-between text-[10px] uppercase tracking-label">
            {STAGES.map((s, i) => (
              <span
                key={s}
                className={i <= view.stage ? "text-mira-muted-text" : "text-mira-disabled"}
              >
                {s}
              </span>
            ))}
          </div>
        </div>
        {interactive && (
          <span className="whitespace-nowrap font-display text-label uppercase tracking-label text-mira-muted-dim transition-colors group-hover:text-mira-lilac-glow">
            open →
          </span>
        )}
      </div>
    </div>
  );
}
