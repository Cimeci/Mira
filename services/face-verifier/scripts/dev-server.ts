// Local dev server for manually exercising the two routes without needing the
// Vercel CLI's login/project-link flow. Not a replacement for `vercel dev` before
// deploying — just a fast loop for testing on your own machine.
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import type { VercelRequest, VercelResponse } from "@vercel/node";
import enrollHandler from "../api/enroll.js";
import verifyHandler from "../api/verify.js";

const routes: Record<string, (req: VercelRequest, res: VercelResponse) => Promise<void>> = {
  "/api/enroll": enrollHandler,
  "/api/verify": verifyHandler,
};

function readJsonBody(req: IncomingMessage): Promise<unknown> {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (chunk) => (data += chunk));
    req.on("end", () => {
      if (!data) {
        resolve(undefined);
        return;
      }
      try {
        resolve(JSON.parse(data));
      } catch (err) {
        reject(err);
      }
    });
    req.on("error", reject);
  });
}

function toVercelResponse(res: ServerResponse): VercelResponse {
  const vres = res as unknown as VercelResponse;
  vres.status = (code: number) => {
    res.statusCode = code;
    return vres;
  };
  vres.json = (body: unknown) => {
    res.setHeader("content-type", "application/json");
    res.end(JSON.stringify(body));
    return vres;
  };
  return vres;
}

const port = Number(process.env.PORT ?? 3000);

createServer(async (req, res) => {
  const handler = req.url ? routes[req.url] : undefined;
  if (!handler) {
    res.statusCode = 404;
    res.end(JSON.stringify({ error: "not_found" }));
    return;
  }

  try {
    const body = await readJsonBody(req);
    const vreq = req as unknown as VercelRequest;
    vreq.body = body;
    await handler(vreq, toVercelResponse(res));
  } catch (err) {
    console.error(err);
    res.statusCode = 500;
    res.end(JSON.stringify({ error: "internal_error" }));
  }
}).listen(port, () => {
  console.log(`face-verifier dev server listening on http://localhost:${port}`);
  console.log("POST /api/enroll  { caseId, imageBase64 }");
  console.log("POST /api/verify  { caseId, sourceUrl, imageBase64, referenceEmbedding? }");
});
