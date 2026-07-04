import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Gitignored — see repo root .gitignore. Mirrors the pattern already used by the
// Python side's .mira_consent/<case_id>.json for consent artifacts.
const EVIDENCE_DIR = path.join(__dirname, "..", ".mira_evidence");
const REFERENCE_DIR = path.join(__dirname, "..", ".mira_reference");

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
