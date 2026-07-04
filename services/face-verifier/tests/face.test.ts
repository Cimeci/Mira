import { createCanvas } from "canvas";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NoFaceDetectedError, computeFaceDescriptor, euclideanDistance } from "../lib/face.js";

/** Synthetic non-face fixture — confirms the model pipeline loads and runs without
 * needing (or risking) any real person's photo. */
function noisePng(size: number): Buffer {
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext("2d");
  const imageData = ctx.createImageData(size, size);
  for (let i = 0; i < imageData.data.length; i += 4) {
    const v = (i * 37) % 256;
    imageData.data[i] = v;
    imageData.data[i + 1] = (v + 60) % 256;
    imageData.data[i + 2] = (v + 120) % 256;
    imageData.data[i + 3] = 255;
  }
  ctx.putImageData(imageData, 0, 0);
  return canvas.toBuffer("image/png");
}

describe("computeFaceDescriptor", () => {
  it("loads the models and throws NoFaceDetectedError on a non-face image", async () => {
    const buf = noisePng(128);
    await expect(computeFaceDescriptor(buf)).rejects.toThrow(NoFaceDetectedError);
  }, 20_000);
});

describe("model loading retry", () => {
  beforeEach(() => {
    // Fresh module instance so the model-loaded cache starts at null — otherwise
    // an earlier test's successful load would short-circuit before ever calling
    // the mocked loadFromDisk below.
    vi.resetModules();
  });

  it("does not permanently cache a rejected model-load promise after a transient failure", async () => {
    const faceapi = await import("face-api.js");
    const spy = vi.spyOn(faceapi.nets.tinyFaceDetector, "loadFromDisk").mockRejectedValueOnce(new Error("boom"));

    const fresh = await import("../lib/face.js");
    const buf = noisePng(128);

    await expect(fresh.computeFaceDescriptor(buf)).rejects.toThrow("boom");

    spy.mockRestore();

    // A second call must retry from scratch rather than rethrowing the same
    // stale "boom" forever — getting NoFaceDetectedError here means it got past
    // model loading and failed only on "no face in this synthetic image", which
    // is the expected, correct outcome.
    await expect(fresh.computeFaceDescriptor(buf)).rejects.toThrow(fresh.NoFaceDetectedError);
  }, 20_000);
});

describe("euclideanDistance", () => {
  it("is zero for identical descriptors", () => {
    const a = new Float32Array([0.1, 0.2, 0.3]);
    expect(euclideanDistance(a, a)).toBe(0);
  });

  it("throws on mismatched descriptor lengths", () => {
    expect(() => euclideanDistance([1, 2], [1, 2, 3])).toThrow();
  });
});
