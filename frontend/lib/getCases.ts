import casesMock from "@/src/mocks/cases.json";

/**
 * The six states a case can be in, in workflow order. Copy is the exact,
 * lowercase status string the UI renders — no separate label lookup.
 */
export type CaseStatus =
  | "collecting evidence"
  | "verifying match"
  | "awaiting your approval"
  | "report sent"
  | "escalated to host"
  | "takedown confirmed";

/** Minimal case summary shown on the dashboard. Never carries content previews. */
export interface CaseSummary {
  id: string;
  platformLabel: string;
  status: CaseStatus;
  lastActivityAt: string;
}

/**
 * Data boundary for the cases dashboard. Today it reads a local mock; swapping
 * in the real event-log API later means changing only this function — the page
 * and components consume `CaseSummary[]` and never touch the source.
 */
export async function getCases(): Promise<CaseSummary[]> {
  return casesMock as CaseSummary[];
}

/** Single-case lookup, used by the detail route. */
export async function getCase(id: string): Promise<CaseSummary | undefined> {
  const cases = await getCases();
  return cases.find((c) => c.id === id);
}
