import { type NextRequest } from "next/server";

/**
 * Same-origin proxy to the local face-verifier service. The browser calls this
 * route (same origin as the app), and Next forwards server-side to the verifier
 * — so there's no cross-origin request and no CORS to configure on the service.
 * Only enroll/verify are exposed; the raw photo is forwarded once, never stored.
 */
const ORIGIN = process.env.FACE_VERIFIER_ORIGIN || "http://localhost:3001";
const ALLOWED = new Set(["enroll", "verify"]);

export async function POST(
  req: NextRequest,
  { params }: { params: { action: string } }
) {
  if (!ALLOWED.has(params.action)) {
    return Response.json({ error: "unknown_action" }, { status: 404 });
  }

  const body = await req.text();
  try {
    const res = await fetch(`${ORIGIN}/api/${params.action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    const text = await res.text();
    return new Response(text, {
      status: res.status,
      headers: {
        "Content-Type": res.headers.get("Content-Type") || "application/json",
      },
    });
  } catch {
    return Response.json(
      { error: "verifier_unreachable", detail: `no response from ${ORIGIN}` },
      { status: 502 }
    );
  }
}
