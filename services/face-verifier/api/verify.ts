// Node.js serverless function (see vercel.json: runtime "nodejs20.x").
// Deliberately NOT `export const config = { runtime: 'edge' }` — face-api.js needs
// the `canvas` native bindings for image decoding, which Edge cannot run.
import type { VercelRequest, VercelResponse } from "@vercel/node";
import { perceptualHash, sha256Hex } from "../lib/hash.js";

const MAX_IMAGE_BYTES = 10 * 1024 * 1024; // 10MB — reject oversized uploads early

interface VerifyRequestBody {
  caseId: string;
  sourceUrl: string;
  imageBase64: string;
}

function isVerifyRequestBody(body: unknown): body is VerifyRequestBody {
  if (!body || typeof body !== "object") return false;
  const b = body as Record<string, unknown>;
  return (
    typeof b.caseId === "string" &&
    typeof b.sourceUrl === "string" &&
    typeof b.imageBase64 === "string"
  );
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "method_not_allowed" });
    return;
  }

  if (!isVerifyRequestBody(req.body)) {
    res.status(400).json({ error: "invalid_body", detail: "caseId, sourceUrl, imageBase64 required" });
    return;
  }

  const { caseId, sourceUrl, imageBase64 } = req.body;

  // Decoded strictly in memory for this request; never written to disk or logged.
  const imageBuffer = Buffer.from(imageBase64, "base64");
  if (imageBuffer.byteLength === 0 || imageBuffer.byteLength > MAX_IMAGE_BYTES) {
    res.status(400).json({ error: "invalid_image_size" });
    return;
  }

  const sha256 = sha256Hex(imageBuffer);
  const phash = await perceptualHash(imageBuffer);

  // Embedding + similarity score land in the next commit (Step 3).
  res.status(200).json({
    caseId,
    sourceUrl,
    sha256Hash: sha256,
    perceptualHash: phash,
  });
}
