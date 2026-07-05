import { DEFAULT_TIMELINE_STEPS, type TimelineStep } from "@/components/case/CaseTimeline";

/**
 * Maps the backend pipeline status (mira.types.Status) onto the UI. Single
 * source of truth so the cases list, the detail card and the timeline all read
 * the same interpretation of a case's state.
 */

/** Human, lowercase label per backend Status. Falls back to the raw value. */
const LABELS: Record<string, string> = {
  MANDATED: "collecting evidence",
  LOCATED: "collecting evidence",
  VERIFIED: "verifying match",
  AWAITING_CONFIRM: "awaiting your approval",
  CONFIRMED: "report sent",
  NOTIFIED: "report sent",
  DECLINED: "on hold",
  ESCALATED: "escalated to host",
  REJECTED: "no match found",
  FAILED: "failed",
  REVOKED: "revoked",
};

export function statusLabel(status: string | null | undefined): string {
  if (!status) return "collecting evidence";
  return LABELS[status] ?? status.toLowerCase();
}

/** Active timeline step index per backend Status (see DEFAULT_TIMELINE_STEPS). */
const STEP: Record<string, number> = {
  MANDATED: 0,
  LOCATED: 0,
  VERIFIED: 1,
  AWAITING_CONFIRM: 2,
  CONFIRMED: 2,
  DECLINED: 2,
  ESCALATED: 3,
  NOTIFIED: 5,
  REJECTED: 1,
  FAILED: 0,
  REVOKED: 0,
};

/** Statuses that mean the whole timeline is done (report sent end-to-end). */
const COMPLETE = new Set(["NOTIFIED"]);

/** Statuses after which nothing else will move on its own. */
const TERMINAL = new Set([
  "NOTIFIED",
  "REJECTED",
  "FAILED",
  "REVOKED",
  "DECLINED",
  "ESCALATED",
]);

/** The G-7 gate is open: mira has a notice ready and is waiting on the victim. */
export function isGateOpen(status: string | null | undefined): boolean {
  return status === "AWAITING_CONFIRM";
}

export function isTerminal(status: string | null | undefined): boolean {
  return status != null && TERMINAL.has(status);
}

/** Derives the timeline (past steps done, current step active) from a status. */
export function timelineFor(status: string | null | undefined): TimelineStep[] {
  const active = status ? (STEP[status] ?? 0) : 0;
  const complete = status != null && COMPLETE.has(status);
  return DEFAULT_TIMELINE_STEPS.map((step, i) => {
    if (complete || i < active) return { ...step, done: true, active: false };
    if (i === active) return { ...step, done: false, active: true };
    return { ...step, done: false, active: false };
  });
}

/** Compact host+path label for a url (drops scheme and trailing slash). */
export function targetLabel(url: string | null | undefined): string {
  if (!url) return "…";
  try {
    const u = new URL(url);
    return (u.host + u.pathname).replace(/\/$/, "") || u.host;
  } catch {
    return url;
  }
}
