import { randomBytes } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  type EvidenceRecord,
  InvalidCaseIdError,
  isValidCaseId,
  loadEvidence,
  loadReferenceEmbedding,
  purgeCase,
  saveEvidence,
  saveReferenceEmbedding,
} from "../lib/store.js";

function testCaseId(): string {
  return `test-${randomBytes(4).toString("hex")}`;
}

// Chemins reconstruits à l'identique de store.ts — délibérément non exportés par le
// module (aucun appelant de prod n'a à connaître le layout disque) ; les tests G-5
// ci-dessous doivent lire les octets bruts pour prouver qu'ils sont chiffrés.
const STORAGE_ROOT = path.join(os.tmpdir(), "mira-face-verifier");
const rawReferencePath = (caseId: string) => path.join(STORAGE_ROOT, "reference", `${caseId}.json`);
const rawEvidencePath = (caseId: string) => path.join(STORAGE_ROOT, "evidence", `${caseId}.json`);

describe("evidence store", () => {
  const caseIds: string[] = [];
  afterEach(async () => {
    await Promise.all(caseIds.splice(0).map((id) => purgeCase(id)));
  });

  it("round-trips a saved evidence record", async () => {
    const caseId = testCaseId();
    caseIds.push(caseId);

    const record: EvidenceRecord = {
      caseId,
      sourceUrl: "https://example.test/photo.jpg",
      sha256Hash: "abc123",
      perceptualHash: "def456",
      similarityScore: 0.87,
      isMatch: true,
      discoveredAt: new Date().toISOString(),
    };

    await saveEvidence(record);
    const loaded = await loadEvidence(caseId);
    expect(loaded).toEqual([record]);
  });

  it("appends multiple records for the same case", async () => {
    const caseId = testCaseId();
    caseIds.push(caseId);

    const base = {
      caseId,
      sourceUrl: "https://example.test/photo.jpg",
      sha256Hash: "a",
      perceptualHash: "0000000000000000",
      similarityScore: null,
      isMatch: false,
      discoveredAt: new Date().toISOString(),
    } satisfies EvidenceRecord;

    // Genuinely different perceptual hash (not just a different sha256) — these
    // represent two distinct images, not a repost of the same one.
    await saveEvidence(base);
    await saveEvidence({ ...base, sha256Hash: "c", perceptualHash: "ffffffffffffffff" });
    const loaded = await loadEvidence(caseId);
    expect(loaded).toHaveLength(2);
  });

  it("returns an empty array for a case with no evidence", async () => {
    expect(await loadEvidence(testCaseId())).toEqual([]);
  });

  it("round-trips a reference embedding", async () => {
    const caseId = testCaseId();
    caseIds.push(caseId);

    const embedding = Array.from({ length: 128 }, (_, i) => i / 128);
    await saveReferenceEmbedding(caseId, embedding);
    expect(await loadReferenceEmbedding(caseId)).toEqual(embedding);
  });

  it("returns null for a case with no enrolled reference", async () => {
    expect(await loadReferenceEmbedding(testCaseId())).toBeNull();
  });

  it("purgeCase removes both evidence and reference", async () => {
    const caseId = testCaseId();
    caseIds.push(caseId);

    await saveReferenceEmbedding(caseId, [0.1, 0.2]);
    await saveEvidence({
      caseId,
      sourceUrl: "https://example.test/photo.jpg",
      sha256Hash: "a",
      perceptualHash: "b",
      similarityScore: null,
      isMatch: false,
      discoveredAt: new Date().toISOString(),
    });

    await purgeCase(caseId);

    expect(await loadEvidence(caseId)).toEqual([]);
    expect(await loadReferenceEmbedding(caseId)).toBeNull();
  });

  it("G-5: never writes a plaintext embedding or evidence to disk", async () => {
    const caseId = testCaseId();
    caseIds.push(caseId);

    const embedding = Array.from({ length: 128 }, (_, i) => i / 128);
    await saveReferenceEmbedding(caseId, embedding);
    await saveEvidence({
      caseId,
      sourceUrl: "https://example.test/secret-location.jpg",
      sha256Hash: "abc123",
      perceptualHash: "def456",
      similarityScore: 0.9,
      isMatch: true,
      discoveredAt: new Date().toISOString(),
    });

    const rawReference = await readFile(rawReferencePath(caseId), "utf-8");
    expect(rawReference).not.toContain("embedding");
    expect(JSON.parse(rawReference)).toMatchObject({ alg: "aes-256-gcm" });

    const rawEvidence = await readFile(rawEvidencePath(caseId), "utf-8");
    expect(rawEvidence).not.toContain("secret-location");
    expect(rawEvidence).not.toContain("sourceUrl");
    expect(JSON.parse(rawEvidence)).toMatchObject({ alg: "aes-256-gcm" });
  });

  it("treats an undecryptable file (legacy plaintext or lost ephemeral key) as absent, not a crash", async () => {
    const caseId = testCaseId();
    caseIds.push(caseId);

    await mkdir(path.dirname(rawReferencePath(caseId)), { recursive: true });
    await mkdir(path.dirname(rawEvidencePath(caseId)), { recursive: true });
    await writeFile(rawReferencePath(caseId), JSON.stringify({ caseId, embedding: [0.1] }), "utf-8");
    await writeFile(rawEvidencePath(caseId), "corrupted-bytes", "utf-8");

    expect(await loadReferenceEmbedding(caseId)).toBeNull();
    expect(await loadEvidence(caseId)).toEqual([]);
  });

  it("isValidCaseId accepts safe identifiers and rejects path-traversal attempts", () => {
    expect(isValidCaseId("demo-case")).toBe(true);
    expect(isValidCaseId("test_ABC-123")).toBe(true);
    expect(isValidCaseId("../../etc/passwd")).toBe(false);
    expect(isValidCaseId("..%2F..%2Fetc%2Fpasswd")).toBe(false);
    expect(isValidCaseId("a/b")).toBe(false);
    expect(isValidCaseId("a\\b")).toBe(false);
    expect(isValidCaseId("a.json")).toBe(false);
    expect(isValidCaseId("")).toBe(false);
  });

  it("rejects a path-traversal caseId before touching the filesystem, for every exported operation", async () => {
    const evilCaseId = "../../.mira_reference/other-case";
    await expect(loadEvidence(evilCaseId)).rejects.toThrow(InvalidCaseIdError);
    await expect(loadReferenceEmbedding(evilCaseId)).rejects.toThrow(InvalidCaseIdError);
    await expect(
      saveEvidence({
        caseId: evilCaseId,
        sourceUrl: "https://example.test",
        sha256Hash: "a",
        perceptualHash: "b",
        similarityScore: null,
        isMatch: false,
        discoveredAt: new Date().toISOString(),
      }),
    ).rejects.toThrow(InvalidCaseIdError);
    await expect(saveReferenceEmbedding(evilCaseId, [0.1])).rejects.toThrow(InvalidCaseIdError);
    await expect(purgeCase(evilCaseId)).rejects.toThrow(InvalidCaseIdError);
  });

  it("serializes concurrent saveEvidence calls for the same case (no lost updates)", async () => {
    const caseId = testCaseId();
    caseIds.push(caseId);

    // Distinct (far-apart) perceptual hashes so none of these get treated as
    // reposts of each other — this test is about the write race, not dedup.
    const makeRecord = (i: number): EvidenceRecord => ({
      caseId,
      sourceUrl: `https://example.test/${i}`,
      sha256Hash: `hash-${i}`,
      perceptualHash: randomBytes(8).toString("hex"),
      similarityScore: null,
      isMatch: false,
      discoveredAt: new Date().toISOString(),
    });

    // Without serialization, these all read the same pre-existing (empty) array
    // before any of them writes, so most records would be lost to last-write-wins.
    await Promise.all(Array.from({ length: 10 }, (_, i) => saveEvidence(makeRecord(i))));

    const loaded = await loadEvidence(caseId);
    expect(loaded).toHaveLength(10);
    expect(new Set(loaded.map((r) => r.sourceUrl)).size).toBe(10);
  });

  it("does not persist a near-duplicate perceptual hash for the same case (repost dedup)", async () => {
    const caseId = testCaseId();
    caseIds.push(caseId);

    const base = {
      caseId,
      sourceUrl: "https://example.test/original.jpg",
      sha256Hash: "a",
      perceptualHash: "0000000000000000",
      similarityScore: null,
      isMatch: false,
      discoveredAt: new Date().toISOString(),
    } satisfies EvidenceRecord;

    await saveEvidence(base);
    // Same image, recompressed elsewhere: different URL/sha256, but perceptual
    // hash within REPOST_HAMMING_THRESHOLD (here, identical) of the one above.
    await saveEvidence({ ...base, sourceUrl: "https://example.test/repost.jpg", sha256Hash: "b" });

    const loaded = await loadEvidence(caseId);
    expect(loaded).toHaveLength(1);
    expect(loaded[0].sourceUrl).toBe("https://example.test/original.jpg");
  });
});
