// Node.js serverless function (see vercel.json: runtime "nodejs20.x").
// Deliberately NOT `export const config = { runtime: 'edge' }` — face-api.js needs
// the `canvas` native bindings for image decoding, which Edge cannot run.
import type { VercelRequest, VercelResponse } from "@vercel/node";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "method_not_allowed" });
    return;
  }

  res.status(501).json({ error: "not_implemented" });
}
