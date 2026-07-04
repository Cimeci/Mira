import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { DecryptError, decryptJson, encryptJson } from "./crypto.js";
import { REPOST_HAMMING_THRESHOLD, hammingDistanceHex } from "./hash.js";

// Vercel's serverless filesystem is read-only everywhere except /tmp — storage
// MUST live under os.tmpdir(), not relative to the deployed function's own
// directory (writing there throws EROFS/EACCES in production even though it
// works fine in local dev, where the whole checkout is writable).
//
// /tmp is ephemeral (not guaranteed to survive a cold start or to be shared
// across instances) — this is a stopgap so the routes don't crash on write,
// not real durable storage. ARCHITECTURE.md already calls for Postgres/Supabase
// as the actual evidence store; this should be replaced by that, not extended.
//
// G-5 : tout ce qui est écrit ici est chiffré au repos (lib/crypto.ts, AES-256-GCM)
// — un fichier indéchiffrable avec la clé courante (reste d'un process précédent
// sous clé éphémère) est traité comme absent, exactement comme un /tmp purgé.
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

// Case IDs come straight from request bodies and get interpolated into
// filesystem paths below — without this, a caseId like "../../etc/passwd"
// (or any path separator/dot-segment) would escape EVIDENCE_DIR/REFERENCE_DIR
// entirely. Enforced here, at the one place every path gets built, so every
// current and future caller of this module is protected, not just whichever
// API route happens to validate its own input today.
const CASE_ID_PATTERN = /^[a-zA-Z0-9_-]{1,128}$/;

/** True only for a caseId safe to use as a filename component. */
export function isValidCaseId(caseId: string): boolean {
  return CASE_ID_PATTERN.test(caseId);
}

export class InvalidCaseIdError extends Error {
  constructor() {
    super("invalid_case_id");
    this.name = "InvalidCaseIdError";
  }
}

function assertValidCaseId(caseId: string): void {
  if (!isValidCaseId(caseId)) {
    throw new InvalidCaseIdError();
  }
}

function evidencePath(caseId: string): string {
  assertValidCaseId(caseId);
  return path.join(EVIDENCE_DIR, `${caseId}.json`);
}

function referencePath(caseId: string): string {
  assertValidCaseId(caseId);
  return path.join(REFERENCE_DIR, `${caseId}.json`);
}

// saveEvidence does a read-modify-write (load the whole array, push, write it all
// back) — two calls for the SAME caseId running concurrently in this process would
// otherwise both read the same pre-existing array and the later write would
// silently clobber the earlier one's record. This queue serializes writes per
// caseId (writes for different cases still run independently/concurrently) so
// each write is guaranteed to see every write queued ahead of it.
const pendingWrites = new Map<string, Promise<void>>();

export async function saveEvidence(record: EvidenceRecord): Promise<void> {
  const previous = pendingWrites.get(record.caseId) ?? Promise.resolve();
  const next = previous.catch(() => {}).then(async () => {
    await ensureDir(EVIDENCE_DIR);
    const existing = await loadEvidence(record.caseId);
    // Same image reposted/recompressed elsewhere for this case — don't store a
    // second near-identical record for what a human reviewer would see as one
    // piece of evidence, not two.
    const isRepost = existing.some(
      (e) => hammingDistanceHex(e.perceptualHash, record.perceptualHash) <= REPOST_HAMMING_THRESHOLD,
    );
    if (isRepost) return;
    existing.push(record);
    await writeFile(evidencePath(record.caseId), encryptJson(existing), "utf-8");
  });
  pendingWrites.set(record.caseId, next);
  try {
    await next;
  } finally {
    // Only remove the entry if nothing new was queued behind this write —
    // otherwise this would delete a later call's still-pending chain.
    if (pendingWrites.get(record.caseId) === next) {
      pendingWrites.delete(record.caseId);
    }
  }
}

export async function loadEvidence(caseId: string): Promise<EvidenceRecord[]> {
  try {
    const raw = await readFile(evidencePath(caseId), "utf-8");
    return decryptJson<EvidenceRecord[]>(raw);
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") return [];
    if (err instanceof DecryptError) {
      console.warn(`[store] evidence for ${caseId} undecryptable with current key — treating as absent`);
      return [];
    }
    throw err;
  }
}

/** The only place a 128-d reference embedding is persisted — keyed by case, never
 * alongside the photo it was derived from (the photo was never written to disk). */
export async function saveReferenceEmbedding(caseId: string, embedding: number[]): Promise<void> {
  await ensureDir(REFERENCE_DIR);
  await writeFile(referencePath(caseId), encryptJson({ caseId, embedding }), "utf-8");
}

export async function loadReferenceEmbedding(caseId: string): Promise<number[] | null> {
  try {
    const raw = await readFile(referencePath(caseId), "utf-8");
    return decryptJson<{ embedding: number[] }>(raw).embedding;
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") return null;
    if (err instanceof DecryptError) {
      console.warn(`[store] reference for ${caseId} undecryptable with current key — treating as absent`);
      return null;
    }
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
