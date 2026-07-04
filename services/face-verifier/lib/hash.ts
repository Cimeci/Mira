import { createHash } from "node:crypto";
import { createCanvas, loadImage } from "canvas";

/** SHA-256 of the exact bytes — the legal-proof hash (any change to the file changes this). */
export function sha256Hex(buffer: Buffer): string {
  return createHash("sha256").update(buffer).digest("hex");
}

const HASH_SIZE = 8; // 8x8 grid -> 64-bit hash

/**
 * Difference hash (dHash): resizes to a tiny grayscale grid and compares adjacent
 * pixel brightness. Survives recompression/resizing/watermarking, unlike SHA-256 —
 * this is what catches the same deepfake reposted elsewhere in a different format.
 */
export async function perceptualHash(buffer: Buffer): Promise<string> {
  const image = await loadImage(buffer);
  const width = HASH_SIZE + 1;
  const height = HASH_SIZE;
  const canvas = createCanvas(width, height);
  const ctx = canvas.getContext("2d");
  ctx.drawImage(image, 0, 0, width, height);
  const { data } = ctx.getImageData(0, 0, width, height);

  const gray: number[] = [];
  for (let i = 0; i < data.length; i += 4) {
    gray.push(0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]);
  }

  let bits = "";
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < HASH_SIZE; x++) {
      const left = gray[y * width + x];
      const right = gray[y * width + x + 1];
      bits += left > right ? "1" : "0";
    }
  }

  let hex = "";
  for (let i = 0; i < bits.length; i += 4) {
    hex += parseInt(bits.slice(i, i + 4), 2).toString(16);
  }
  return hex;
}

/** Hamming distance between two hex-encoded perceptual hashes — smaller means more similar. */
export function hammingDistanceHex(a: string, b: string): number {
  if (a.length !== b.length) return Number.POSITIVE_INFINITY;
  let distance = 0;
  for (let i = 0; i < a.length; i++) {
    let x = parseInt(a[i], 16) ^ parseInt(b[i], 16);
    while (x) {
      distance += x & 1;
      x >>= 1;
    }
  }
  return distance;
}
