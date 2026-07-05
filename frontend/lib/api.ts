/**
 * Backend boundary for the live pipeline (FastAPI, mira/api.py). The dashboard still
 * reads mocks (getCases.ts); this is the ONE place the intake flow talks to the real
 * backend. Base URL is overridable so the demo can point at a deployed API.
 */
const API_BASE =
  process.env.NEXT_PUBLIC_MIRA_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export interface ScoutDispatch {
  case_id: string;
  state_url: string;
  events_url: string;
}

/**
 * Dispatch the Computer Use scout for a freshly-opened case. The backend creates the
 * case, launches the scout in the background, and streams located image URLs; this
 * call returns as soon as the case is registered (the scan runs async).
 */
export async function dispatchScout(url: string): Promise<ScoutDispatch> {
  const res = await fetch(`${API_BASE}/scout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    // Never swallow: surface the backend's reason (400 out-of-scope, 409, …) to the UI.
    throw new Error(`scout dispatch failed (${res.status}): ${await res.text()}`);
  }
  return res.json();
}
