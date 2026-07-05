"use client";

/**
 * Thin client for the local face-verifier service (services/face-verifier).
 * The scan enrolls the victim's live face (real face detection → a hand/no-face
 * is rejected here, not client-side heuristics); case opening verifies the
 * suspected content against that reference. Only embeddings cross the wire — the
 * raw photo is decoded in-memory by the local service and never persisted.
 */

// Same-origin proxy (see app/api/face/[action]/route.ts) — avoids CORS entirely:
// the browser calls the app, Next forwards to the face-verifier server-side.
const BASE = "/api/face";

/** The enroll/verify APIs want raw base64; a canvas/blob data URL carries a prefix. */
function stripDataUrl(dataUrl: string): string {
  const comma = dataUrl.indexOf(",");
  return comma >= 0 ? dataUrl.slice(comma + 1) : dataUrl;
}

export type EnrollResult =
  | { ok: true; embedding: number[] }
  | { ok: false; reason: "no_face" | "error"; detail?: string };

/** Enrolls a live face frame → 128-d reference embedding. 422 = no detectable face. */
export async function enrollFace(
  caseId: string,
  imageDataUrl: string
): Promise<EnrollResult> {
  try {
    const res = await fetch(`${BASE}/enroll`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ caseId, imageBase64: stripDataUrl(imageDataUrl) }),
    });
    if (res.status === 422) return { ok: false, reason: "no_face" };
    if (!res.ok) return { ok: false, reason: "error", detail: `status ${res.status}` };
    const data = (await res.json()) as { embedding?: number[] };
    if (!Array.isArray(data.embedding)) {
      return { ok: false, reason: "error", detail: "no embedding returned" };
    }
    return { ok: true, embedding: data.embedding };
  } catch {
    return { ok: false, reason: "error", detail: "verifier unreachable" };
  }
}

export type VerifyResult =
  | { ok: true; isMatch: boolean; similarityScore: number | null; noFaceDetected: boolean }
  | { ok: false; reason: string };

/** Verifies suspected content bytes against the enrolled reference embedding. */
export async function verifyFace(params: {
  caseId: string;
  sourceUrl: string;
  imageDataUrl: string;
  referenceEmbedding: number[];
}): Promise<VerifyResult> {
  try {
    const res = await fetch(`${BASE}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        caseId: params.caseId,
        sourceUrl: params.sourceUrl,
        imageBase64: stripDataUrl(params.imageDataUrl),
        referenceEmbedding: params.referenceEmbedding,
      }),
    });
    if (!res.ok) return { ok: false, reason: `status ${res.status}` };
    const d = (await res.json()) as {
      isMatch?: boolean;
      similarityScore?: number | null;
      noFaceDetected?: boolean;
    };
    return {
      ok: true,
      isMatch: Boolean(d.isMatch),
      similarityScore: d.similarityScore ?? null,
      noFaceDetected: Boolean(d.noFaceDetected),
    };
  } catch {
    return { ok: false, reason: "verifier unreachable" };
  }
}

/**
 * Fetches a remote image and returns a data URL, or null if it can't be
 * retrieved (CORS-blocked, 404, or not an image). Used to pull the suspected
 * content bytes for /verify — there is no scraper, so the content must be a
 * directly reachable image URL.
 */
export async function fetchImageAsDataUrl(url: string): Promise<string | null> {
  try {
    const res = await fetch(url, { mode: "cors" });
    if (!res.ok) return null;
    const blob = await res.blob();
    if (!blob.type.startsWith("image/")) return null;
    return await new Promise<string | null>((resolve) => {
      const reader = new FileReader();
      reader.onloadend = () =>
        resolve(typeof reader.result === "string" ? reader.result : null);
      reader.onerror = () => resolve(null);
      reader.readAsDataURL(blob);
    });
  } catch {
    return null;
  }
}
