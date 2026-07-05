import { statusLabel, targetLabel } from "./caseProgress";

/** Human status string rendered by the UI (derived from the backend Status). */
export type CaseStatus = string;

/** Minimal case summary shown on the dashboard. Never carries content previews. */
export interface CaseSummary {
  id: string;
  platformLabel: string;
  status: CaseStatus;
  lastActivityAt: string;
}

/** Shape returned by GET /cases (mira/api.py: list_cases). */
interface BackendCase {
  case_id: string;
  finished: boolean;
  current_status: string | null;
  statuses: Record<string, string>;
  created_at: string | null;
}

function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE || "";
}

function toSummary(c: BackendCase): CaseSummary {
  // The scope url is only exposed once the pipeline records per-url statuses;
  // before that the case id is the stable handle we can show.
  const firstTarget = Object.keys(c.statuses ?? {})[0];
  return {
    id: c.case_id,
    platformLabel: firstTarget ? targetLabel(firstTarget) : c.case_id,
    status: statusLabel(c.current_status),
    lastActivityAt: c.created_at ?? "",
  };
}

/**
 * Data boundary for the cases dashboard. Reads the live backend case registry
 * (GET /cases). A dead backend yields an empty list rather than a crashed page.
 */
export async function getCases(): Promise<CaseSummary[]> {
  try {
    const res = await fetch(`${apiBase()}/cases`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = (await res.json()) as { cases?: BackendCase[] };
    return (data.cases ?? []).map(toSummary);
  } catch {
    return [];
  }
}
