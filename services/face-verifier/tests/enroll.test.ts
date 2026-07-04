import { randomBytes } from "node:crypto";
import { afterEach, describe, expect, it } from "vitest";
import enrollHandler from "../api/enroll.js";
import { loadReferenceEmbedding, purgeCase } from "../lib/store.js";

function testCaseId(): string {
  return `test-${randomBytes(4).toString("hex")}`;
}

function mockReq(method: string, body: unknown) {
  return { method, body } as Parameters<typeof enrollHandler>[0];
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
  return res as unknown as Parameters<typeof enrollHandler>[1] & typeof res;
}

describe("POST /api/enroll", () => {
  const caseIds: string[] = [];
  afterEach(async () => {
    await Promise.all(caseIds.splice(0).map((id) => purgeCase(id)));
  });

  it("accepts a pre-computed embedding and persists it without ever touching an image", async () => {
    const caseId = testCaseId();
    caseIds.push(caseId);
    const embedding = Array.from({ length: 128 }, (_, i) => i / 128);

    const res = mockRes();
    await enrollHandler(mockReq("POST", { caseId, embedding }), res);

    expect(res.statusCode).toBe(200);
    expect(res.body).toEqual({ caseId, embedding });
    expect(await loadReferenceEmbedding(caseId)).toEqual(embedding);
  });

  it("rejects an embedding with the wrong dimensionality", async () => {
    const caseId = testCaseId();
    caseIds.push(caseId);

    const res = mockRes();
    await enrollHandler(mockReq("POST", { caseId, embedding: [1, 2, 3] }), res);

    expect(res.statusCode).toBe(400);
    expect(res.body).toMatchObject({ error: "invalid_embedding" });
    expect(await loadReferenceEmbedding(caseId)).toBeNull();
  });

  it("rejects a body with neither embedding nor imageBase64", async () => {
    const res = mockRes();
    await enrollHandler(mockReq("POST", { caseId: testCaseId() }), res);

    expect(res.statusCode).toBe(400);
    expect(res.body).toMatchObject({ error: "invalid_body" });
  });

  it("rejects non-POST methods", async () => {
    const res = mockRes();
    await enrollHandler(mockReq("GET", {}), res);
    expect(res.statusCode).toBe(405);
  });
});
