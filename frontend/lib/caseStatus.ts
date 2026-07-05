/**
 * Maps a raw pipeline status (mira.types.Status) to how a case card presents it:
 * a human label, a semantic tone, and how far along the collect→verify→notify
 * tracker it is. Single source of truth so the dashboard and any future case UI
 * agree on wording and color.
 */

export type CaseTone = "active" | "action" | "done" | "halted";

export interface CaseStatusView {
  label: string;
  tone: CaseTone;
  /** Completed stages out of 3 (collect · verify · notify). */
  stage: number;
  /** True when the case is blocked on the victim (gate G-7). */
  needsAction: boolean;
}

const VIEWS: Record<string, CaseStatusView> = {
  MANDATED: { label: "collecting evidence", tone: "active", stage: 0, needsAction: false },
  LOCATED: { label: "evidence located", tone: "active", stage: 1, needsAction: false },
  VERIFIED: { label: "match verified", tone: "active", stage: 2, needsAction: false },
  AWAITING_CONFIRM: { label: "needs your approval", tone: "action", stage: 2, needsAction: true },
  NOTIFIED: { label: "takedown requested", tone: "done", stage: 3, needsAction: false },
  CONFIRMED: { label: "takedown confirmed", tone: "done", stage: 3, needsAction: false },
  DECLINED: { label: "declined — on hold", tone: "halted", stage: 2, needsAction: false },
};

const STARTING: CaseStatusView = {
  label: "opening case",
  tone: "active",
  stage: 0,
  needsAction: false,
};

export function caseStatusView(raw: string | null): CaseStatusView {
  if (!raw) return STARTING;
  return VIEWS[raw] ?? { ...STARTING, label: raw.toLowerCase().replace(/_/g, " ") };
}

/** Compact "3m ago" / "2h ago" from an ISO timestamp; empty on missing input. */
export function relativeTime(iso: string | null, now = Date.now()): string {
  if (!iso) return "";
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return "";
  const secs = Math.max(0, Math.round((now - then) / 1000));
  if (secs < 45) return "just now";
  const mins = Math.round(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}
