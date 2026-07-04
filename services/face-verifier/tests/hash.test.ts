import { createCanvas } from "canvas";
import { describe, expect, it } from "vitest";
import { hammingDistanceHex, perceptualHash, sha256Hex } from "../lib/hash.js";

/**
 * Synthetic diagonal-gradient fixture — never a real photo, just for hash-behavior
 * tests. Built via putImageData (raw pixel buffer) rather than fillStyle/gradients:
 * some Canvas/Cairo builds mis-render gradient fills, but the raw pixel path is
 * exactly what production decoding (loadImage -> drawImage -> getImageData) uses.
 */
function gradientPng(size: number, fromValue: number, toValue: number): Buffer {
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext("2d");
  const imageData = ctx.createImageData(size, size);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const t = (x + y) / (2 * (size - 1));
      const value = Math.round(fromValue + (toValue - fromValue) * t);
      const i = (y * size + x) * 4;
      imageData.data[i] = value;
      imageData.data[i + 1] = value;
      imageData.data[i + 2] = value;
      imageData.data[i + 3] = 255;
    }
  }
  ctx.putImageData(imageData, 0, 0);
  return canvas.toBuffer("image/png");
}

describe("sha256Hex", () => {
  it("is deterministic for identical bytes", () => {
    const buf = gradientPng(64, 0, 255);
    expect(sha256Hex(buf)).toBe(sha256Hex(buf));
  });

  it("differs for different bytes", () => {
    const a = gradientPng(64, 0, 255);
    const b = gradientPng(64, 255, 0);
    expect(sha256Hex(a)).not.toBe(sha256Hex(b));
  });
});

describe("perceptualHash", () => {
  it("is deterministic and a 64-bit (16 hex char) hash", async () => {
    const buf = gradientPng(64, 0, 255);
    const hash = await perceptualHash(buf);
    expect(hash).toHaveLength(16);
    expect(await perceptualHash(buf)).toBe(hash);
  });

  it("differs meaningfully for a visually inverted image", async () => {
    const a = await perceptualHash(gradientPng(64, 0, 255));
    const b = await perceptualHash(gradientPng(64, 255, 0));
    expect(hammingDistanceHex(a, b)).toBeGreaterThan(20);
  });

  it("stays close for the same image re-encoded at a different size (repost tolerance)", async () => {
    const original = await perceptualHash(gradientPng(64, 40, 220));
    const resized = await perceptualHash(gradientPng(128, 40, 220));
    expect(hammingDistanceHex(original, resized)).toBeLessThanOrEqual(4);
  });
});
