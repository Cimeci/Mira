// Node.js serverless function (see vercel.json: runtime "nodejs20.x").
// Deliberately NOT `export const config = { runtime: 'edge' }` — face-api.js needs
// the `canvas` native bindings for image decoding, which Edge cannot run.
import type { VercelRequest, VercelResponse } from "@vercel/node";
import {
  MATCH_DISTANCE_THRESHOLD,
  NoFaceDetectedError,
  computeFaceDescriptor,
  euclideanDistance,
  similarityFromDistance,
} from "../lib/face.js";
import { perceptualHash, sha256Hex } from "../lib/hash.js";
import { type EvidenceRecord, loadReferenceEmbedding, saveEvidence } from "../lib/store.js";

const MAX_IMAGE_BYTES = 10 * 1024 * 1024; // 10MB — reject oversized uploads early

interface VerifyRequestBody {
  caseId: string;
  sourceUrl: string;
  imageBase64: string;
  /** Optional override — normally looked up from the enrolled reference by caseId. */
  referenceEmbedding?: number[];
}

function isVerifyRequestBody(body: unknown): body is VerifyRequestBody {
  if (!body || typeof body !== "object") return false;
  const b = body as Record<string, unknown>;
  const embeddingOk =
    b.referenceEmbedding === undefined ||
    (Array.isArray(b.referenceEmbedding) && b.referenceEmbedding.every((n) => typeof n === "number"));
  return (
    typeof b.caseId === "string" &&
    typeof b.sourceUrl === "string" &&
    typeof b.imageBase64 === "string" &&
    embeddingOk
  );
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "method_not_allowed" });
    return;
  }

  if (!isVerifyRequestBody(req.body)) {
    res.status(400).json({
      error: "invalid_body",
      detail: "caseId, sourceUrl, imageBase64 required (referenceEmbedding optional override)",
    });
    return;
  }

  const { caseId, sourceUrl, imageBase64 } = req.body;

  const referenceEmbedding = req.body.referenceEmbedding ?? (await loadReferenceEmbedding(caseId));
  if (!referenceEmbedding) {
    res.status(400).json({ error: "no_reference_enrolled", detail: "call /api/enroll for this caseId first" });
    return;
  }

  // Decoded strictly in memory for this request; never written to disk or logged.
  const imageBuffer = Buffer.from(imageBase64, "base64");
  if (imageBuffer.byteLength === 0 || imageBuffer.byteLength > MAX_IMAGE_BYTES) {
    res.status(400).json({ error: "invalid_image_size" });
    return;
  }

  const sha256Hash = sha256Hex(imageBuffer);
  const perceptualHashValue = await perceptualHash(imageBuffer);
  const discoveredAt = new Date().toISOString();

  let similarityScore: number | null = null;
  let isMatch = false;
  let noFaceDetected = false;

  try {
    const descriptor = await computeFaceDescriptor(imageBuffer);
    const distance = euclideanDistance(descriptor, referenceEmbedding);
    similarityScore = similarityFromDistance(distance);
    isMatch = distance < MATCH_DISTANCE_THRESHOLD;
  } catch (err) {
    if (!(err instanceof NoFaceDetectedError)) throw err;
    // Still evidence-worthy — a hashable image with no detectable face is a real
    // outcome, not a request failure.
    noFaceDetected = true;
  }

  // Only hash + score fields are persisted — this type has no field for image bytes.
  const record: EvidenceRecord = {
    caseId,
    sourceUrl,
    sha256Hash,
    perceptualHash: perceptualHashValue,
    similarityScore,
    isMatch,
    discoveredAt,
  };
  await saveEvidence(record);

  res.status(200).json({ ...record, noFaceDetected });
}
