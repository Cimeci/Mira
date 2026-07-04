import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

// Vercel's serverless filesystem is read-only everywhere except /tmp — storage
// MUST live under os.tmpdir(), not relative to the deployed function's own
// directory (writing there throws EROFS/EACCES in production even though it
// works fine in local dev, where the whole checkout is writable).
//
// /tmp is ephemeral (not guaranteed to survive a cold start or to be shared
// across instances) — this is a stopgap so the routes don't crash on write,
// not real durable storage. ARCHITECTURE.md already calls for Postgres/Supabase
// as the actual evidence store; this should be replaced by that, not extended.
const STORAGE_ROOT = path.join(os.tmpdir(), "mira-face-verifier");
const EVIDENCE_DIR = path.join(STORAGE_ROOT, "evidence");
const REFERENCE_DIR = path.join(STORAGE_ROOT, "reference");

/**
 * What gets persisted for a candidate image — hash + embedding + score only.
 * No image bytes, no base64, no data URL: this type has no field that could hold one.
 */
export interface EvidenceRecord {
  caseId: string;
  sourceUrl: string;
  sha256Hash: string;
  perceptualHash: string;
  similarityScore: number | null;
  isMatch: boolean;
  discoveredAt: string;
}

async function ensureDir(dir: string): Promise<void> {
  await mkdir(dir, { recursive: true });
}

function evidencePath(caseId: string): string {
  return path.join(EVIDENCE_DIR, `${caseId}.json`);
}

function referencePath(caseId: string): string {
  return path.join(REFERENCE_DIR, `${caseId}.json`);
}

export async function saveEvidence(record: EvidenceRecord): Promise<void> {
  await ensureDir(EVIDENCE_DIR);
  const existing = await loadEvidence(record.caseId);
  existing.push(record);
  await writeFile(evidencePath(record.caseId), JSON.stringify(existing, null, 2), "utf-8");
}

export async function loadEvidence(caseId: string): Promise<EvidenceRecord[]> {
  try {
    const raw = await readFile(evidencePath(caseId), "utf-8");
    return JSON.parse(raw) as EvidenceRecord[];
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") return [];
    throw err;
  }
}

/** The only place a 128-d reference embedding is persisted — keyed by case, never
 * alongside the photo it was derived from (the photo was never written to disk). */
export async function saveReferenceEmbedding(caseId: string, embedding: number[]): Promise<void> {
  await ensureDir(REFERENCE_DIR);
  await writeFile(referencePath(caseId), JSON.stringify({ caseId, embedding }), "utf-8");
}

export async function loadReferenceEmbedding(caseId: string): Promise<number[] | null> {
  try {
    const raw = await readFile(referencePath(caseId), "utf-8");
    return (JSON.parse(raw) as { embedding: number[] }).embedding;
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw err;
  }
}

/**
 * Deletes all persisted evidence and the reference embedding for a case.
 * Not wired to any trigger yet — ready for whoever implements the mandate-revocation
 * -> purge flow (G-8) to call this.
 */
export async function purgeCase(caseId: string): Promise<void> {
  await Promise.all([
    rm(evidencePath(caseId), { force: true }),
    rm(referencePath(caseId), { force: true }),
  ]);
}
