import { randomBytes } from "node:crypto";
import { afterEach, describe, expect, it } from "vitest";
import { DecryptError, decryptJson, encryptJson, resetKeyForTests } from "../lib/crypto.js";

describe("crypto envelope (G-5 at-rest encryption)", () => {
  afterEach(() => {
    delete process.env.EVIDENCE_ENCRYPTION_KEY;
    resetKeyForTests();
  });

  it("round-trips a JSON value", () => {
    const value = { caseId: "demo", embedding: [0.1, 0.2, 0.3] };
    expect(decryptJson(encryptJson(value))).toEqual(value);
  });

  it("never leaks plaintext into the envelope", () => {
    const raw = encryptJson({ secret: "biometric-embedding-value", sourceUrl: "https://x.test" });
    expect(raw).not.toContain("biometric-embedding-value");
    expect(raw).not.toContain("sourceUrl");
    expect(JSON.parse(raw)).toMatchObject({ alg: "aes-256-gcm" });
  });

  it("throws DecryptError on a tampered envelope (GCM auth tag)", () => {
    const envelope = JSON.parse(encryptJson({ v: 1 })) as { data: string };
    const bytes = Buffer.from(envelope.data, "base64");
    bytes[0] ^= 0xff;
    envelope.data = bytes.toString("base64");
    expect(() => decryptJson(JSON.stringify(envelope))).toThrow(DecryptError);
  });

  it("throws DecryptError on non-envelope input (legacy plaintext file)", () => {
    expect(() => decryptJson(JSON.stringify({ caseId: "x", embedding: [1] }))).toThrow(DecryptError);
    expect(() => decryptJson("not even json")).toThrow(DecryptError);
  });

  it("uses EVIDENCE_ENCRYPTION_KEY from the env when set, stable across key-cache resets", () => {
    process.env.EVIDENCE_ENCRYPTION_KEY = randomBytes(32).toString("base64");
    resetKeyForTests();
    const raw = encryptJson({ v: 42 });
    // Un nouveau process avec la MÊME clé env doit pouvoir déchiffrer — simulé
    // en purgeant le cache : si la clé env n'était pas relue, ceci échouerait.
    resetKeyForTests();
    expect(decryptJson(raw)).toEqual({ v: 42 });
  });

  it("fails fast on a malformed EVIDENCE_ENCRYPTION_KEY instead of silently falling back", () => {
    process.env.EVIDENCE_ENCRYPTION_KEY = "too-short";
    resetKeyForTests();
    expect(() => encryptJson({ v: 1 })).toThrow(/32 bytes/);
  });

  it("data written under a lost ephemeral key becomes undecryptable (DecryptError, not garbage)", () => {
    const raw = encryptJson({ v: 1 });
    resetKeyForTests(); // nouveau process, nouvelle clé éphémère
    expect(() => decryptJson(raw)).toThrow(DecryptError);
  });
});
