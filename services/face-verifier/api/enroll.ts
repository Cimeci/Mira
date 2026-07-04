// Node.js serverless function (see vercel.json: runtime "nodejs20.x").
// Deliberately NOT `export const config = { runtime: 'edge' }` — face-api.js needs
// the `canvas` native bindings for image decoding, which Edge cannot run.
import type { VercelRequest, VercelResponse } from "@vercel/node";
import { NoFaceDetectedError, computeFaceDescriptor } from "../lib/face.js";

const MAX_IMAGE_BYTES = 10 * 1024 * 1024; // 10MB

interface EnrollRequestBody {
  caseId: string;
  imageBase64: string;
}

function isEnrollRequestBody(body: unknown): body is EnrollRequestBody {
  if (!body || typeof body !== "object") return false;
  const b = body as Record<string, unknown>;
  return typeof b.caseId === "string" && typeof b.imageBase64 === "string";
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "method_not_allowed" });
    return;
  }

  if (!isEnrollRequestBody(req.body)) {
    res.status(400).json({ error: "invalid_body", detail: "caseId, imageBase64 required" });
    return;
  }

  const { caseId, imageBase64 } = req.body;

  // Decoded strictly in memory for this request; never written to disk or logged.
  // Only the resulting embedding is returned — the photo itself never leaves this scope.
  const imageBuffer = Buffer.from(imageBase64, "base64");
  if (imageBuffer.byteLength === 0 || imageBuffer.byteLength > MAX_IMAGE_BYTES) {
    res.status(400).json({ error: "invalid_image_size" });
    return;
  }

  try {
    const descriptor = await computeFaceDescriptor(imageBuffer);
    res.status(200).json({
      caseId,
      embedding: Array.from(descriptor),
    });
  } catch (err) {
    if (err instanceof NoFaceDetectedError) {
      res.status(422).json({ error: "no_face_detected" });
      return;
    }
    throw err;
  }
}
