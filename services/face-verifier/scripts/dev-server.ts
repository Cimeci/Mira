// Local dev server for manually exercising the two routes without needing the
// Vercel CLI's login/project-link flow. Not a replacement for `vercel dev` before
// deploying — just a fast loop for testing on your own machine.
import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { VercelRequest, VercelResponse } from "@vercel/node";
import enrollHandler from "../api/enroll.js";
import verifyHandler from "../api/verify.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = path.join(__dirname, "..", "public");

const routes: Record<string, (req: VercelRequest, res: VercelResponse) => Promise<void>> = {
  "/api/enroll": enrollHandler,
  "/api/verify": verifyHandler,
};

const CONTENT_TYPES: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json",
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

/** Serves static files under public/ (scan.html, face-api.js browser bundle, model
 * weights) — mirrors how Vercel serves anything outside api/ as a static asset. */
function serveStatic(req: IncomingMessage, res: ServerResponse): boolean {
  const urlPath = (req.url ?? "/").split("?")[0];
  const relative = urlPath === "/" ? "/scan.html" : urlPath;
  const filePath = path.join(PUBLIC_DIR, relative);

  // Prevent path traversal outside PUBLIC_DIR. A plain startsWith(PUBLIC_DIR)
  // would also match a sibling directory sharing the same string prefix (e.g.
  // "public-evil" starts with "public") — require an exact match or a real
  // path-separator boundary.
  const isInsidePublicDir = filePath === PUBLIC_DIR || filePath.startsWith(PUBLIC_DIR + path.sep);
  if (!isInsidePublicDir || !existsSync(filePath) || !statSync(filePath).isFile()) {
    return false;
  }

  const ext = path.extname(filePath);
  res.setHeader("content-type", CONTENT_TYPES[ext] ?? "application/octet-stream");
  createReadStream(filePath).pipe(res);
  return true;
}

const port = Number(process.env.PORT ?? 3000);

createServer(async (req, res) => {
  const handler = req.url ? routes[req.url.split("?")[0]] : undefined;
  if (handler) {
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
    return;
  }

  if (req.method === "GET" && serveStatic(req, res)) return;

  res.statusCode = 404;
  res.end(JSON.stringify({ error: "not_found" }));
}).listen(port, () => {
  console.log(`face-verifier dev server listening on http://localhost:${port}`);
  console.log("POST /api/enroll  { caseId, imageBase64 | embedding }");
  console.log("POST /api/verify  { caseId, sourceUrl, imageBase64, referenceEmbedding? }");
  console.log(`GET  /scan.html   in-browser webcam scan proof-of-concept`);
}).on("error", (err) => {
  console.error(err);
  process.exit(1);
});
