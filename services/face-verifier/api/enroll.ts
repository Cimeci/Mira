// Node.js serverless function (see vercel.json: runtime "nodejs20.x").
// Deliberately NOT `export const config = { runtime: 'edge' }` — face-api.js needs
// the `canvas` native bindings for image decoding, which Edge cannot run.
import type { VercelRequest, VercelResponse } from "@vercel/node";
import { NoFaceDetectedError, computeFaceDescriptor, isValidDescriptor } from "../lib/face.js";
import { saveReferenceEmbedding } from "../lib/store.js";

const MAX_IMAGE_BYTES = 10 * 1024 * 1024; // 10MB

interface EnrollRequestBody {
  caseId: string;
  /** Preferred path: the browser already computed this locally (face-api.js in the
   * browser) — the photo itself never left the device. */
  embedding?: number[];
  /** Fallback path: raw photo, embedding computed here server-side. */
  imageBase64?: string;
}

function isEnrollRequestBody(body: unknown): body is EnrollRequestBody {
  if (!body || typeof body !== "object") return false;
  const b = body as Record<string, unknown>;
  if (typeof b.caseId !== "string") return false;
  if (b.embedding !== undefined) return true; // shape checked by isValidDescriptor below
  return typeof b.imageBase64 === "string";
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "method_not_allowed" });
    return;
  }

  if (!isEnrollRequestBody(req.body)) {
    res.status(400).json({
      error: "invalid_body",
      detail: "caseId required, plus one of: embedding (preferred) or imageBase64",
    });
    return;
  }

  const { caseId } = req.body;

  // Client already computed the embedding (e.g. in-browser scan) — the photo was
  // never sent to us at all. This is the preferred path.
  if (req.body.embedding !== undefined) {
    if (!isValidDescriptor(req.body.embedding)) {
      res.status(400).json({ error: "invalid_embedding", detail: "expected 128 finite numbers" });
      return;
    }
    await saveReferenceEmbedding(caseId, req.body.embedding);
    res.status(200).json({ caseId, embedding: req.body.embedding });
    return;
  }

  // Fallback: caller sent a photo, we compute the embedding here.
  // Decoded strictly in memory for this request; never written to disk or logged.
  // Only the resulting embedding is persisted — the photo itself never leaves this scope.
  const imageBuffer = Buffer.from(req.body.imageBase64 as string, "base64");
  if (imageBuffer.byteLength === 0 || imageBuffer.byteLength > MAX_IMAGE_BYTES) {
    res.status(400).json({ error: "invalid_image_size" });
    return;
  }

  try {
    const descriptor = await computeFaceDescriptor(imageBuffer);
    const embedding = Array.from(descriptor);
    await saveReferenceEmbedding(caseId, embedding);
    res.status(200).json({ caseId, embedding });
  } catch (err) {
    if (err instanceof NoFaceDetectedError) {
      res.status(422).json({ error: "no_face_detected" });
      return;
    }
    throw err;
  }
}
