import { randomBytes } from "node:crypto";
import { afterEach, describe, expect, it } from "vitest";
import verifyHandler from "../api/verify.js";
import { purgeCase } from "../lib/store.js";

function testCaseId(): string {
  return `test-${randomBytes(4).toString("hex")}`;
}

function mockReq(method: string, body: unknown) {
  return { method, body } as Parameters<typeof verifyHandler>[0];
}

function mockRes() {
  const res = {
    statusCode: 0,
    body: undefined as unknown,
    status(code: number) {
      res.statusCode = code;
      return res;
    },
    json(payload: unknown) {
      res.body = payload;
      return res;
    },
  };
  return res as unknown as Parameters<typeof verifyHandler>[1] & typeof res;
}

describe("POST /api/verify", () => {
  const caseIds: string[] = [];
  afterEach(async () => {
    await Promise.all(caseIds.splice(0).map((id) => purgeCase(id)));
  });

  // These all fail validation before the image is ever decoded, so imageBase64
  // doesn't need to be a real image.

  it("rejects a referenceEmbedding override with the wrong dimensionality (not a 500)", async () => {
    const caseId = testCaseId();
    caseIds.push(caseId);

    const res = mockRes();
    await verifyHandler(
      mockReq("POST", {
        caseId,
        sourceUrl: "https://example.test",
        imageBase64: "x",
        referenceEmbedding: [1, 2, 3],
      }),
      res,
    );

    expect(res.statusCode).toBe(400);
    expect(res.body).toMatchObject({ error: "invalid_embedding" });
  });

  it("rejects a referenceEmbedding override containing NaN", async () => {
    const caseId = testCaseId();
    caseIds.push(caseId);
    const badEmbedding = Array.from({ length: 128 }, (_, i) => (i === 0 ? Number.NaN : i / 128));

    const res = mockRes();
    await verifyHandler(
      mockReq("POST", {
        caseId,
        sourceUrl: "https://example.test",
        imageBase64: "x",
        referenceEmbedding: badEmbedding,
      }),
      res,
    );

    expect(res.statusCode).toBe(400);
    expect(res.body).toMatchObject({ error: "invalid_embedding" });
  });

  it("rejects a path-traversal caseId with a clean 400, not a 500", async () => {
    const res = mockRes();
    await verifyHandler(
      mockReq("POST", {
        caseId: "../../.mira_reference/other-case",
        sourceUrl: "https://example.test",
        imageBase64: "x",
        referenceEmbedding: Array(128).fill(0),
      }),
      res,
    );

    expect(res.statusCode).toBe(400);
    expect(res.body).toMatchObject({ error: "invalid_case_id" });
  });

  it("returns no_reference_enrolled when no override is given and nothing was enrolled for this case", async () => {
    const res = mockRes();
    await verifyHandler(
      mockReq("POST", { caseId: testCaseId(), sourceUrl: "https://example.test", imageBase64: "x" }),
      res,
    );

    expect(res.statusCode).toBe(400);
    expect(res.body).toMatchObject({ error: "no_reference_enrolled" });
  });

  it("rejects a body missing required fields", async () => {
    const res = mockRes();
    await verifyHandler(mockReq("POST", { caseId: testCaseId() }), res);

    expect(res.statusCode).toBe(400);
    expect(res.body).toMatchObject({ error: "invalid_body" });
  });

  it("rejects non-POST methods", async () => {
    const res = mockRes();
    await verifyHandler(mockReq("GET", {}), res);
    expect(res.statusCode).toBe(405);
  });
});
