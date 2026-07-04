import { Canvas, Image, ImageData, createCanvas } from "canvas";
import * as faceapi from "face-api.js";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { type ImageInput, toImage } from "./image.js";

// face-api.js expects browser DOM globals (Canvas/Image/ImageData) — provide them
// via node-canvas. Must run before any faceapi.nets.* call.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
faceapi.env.monkeyPatch({ Canvas: Canvas as any, Image: Image as any, ImageData: ImageData as any });

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const MODELS_DIR = path.join(__dirname, "..", "models");

/** Recommended by face-api.js for its 128-d recognition descriptor: below this
 * Euclidean distance, two descriptors are considered the same person. */
export const MATCH_DISTANCE_THRESHOLD = 0.6;

export const DESCRIPTOR_LENGTH = 128;

/** True only for a well-formed 128-d descriptor — used to validate an embedding
 * a client computed itself (e.g. in-browser) before we trust and persist it. */
export function isValidDescriptor(value: unknown): value is number[] {
  return (
    Array.isArray(value) &&
    value.length === DESCRIPTOR_LENGTH &&
    value.every((n) => typeof n === "number" && Number.isFinite(n))
  );
}

let modelsLoaded: Promise<void> | null = null;

/** Loads model weights once per cold start (module-level singleton) — avoids
 * re-reading ~7MB of weights from disk on every invocation of a warm function.
 *
 * On failure, resets the cache to null before rethrowing: a transient error
 * (e.g. the models directory not yet fully available on a cold container)
 * must not permanently poison every future call in this warm instance — the
 * next call should get a fresh attempt, not the same stale rejection forever. */
function ensureModelsLoaded(): Promise<void> {
  if (!modelsLoaded) {
    modelsLoaded = Promise.all([
      faceapi.nets.tinyFaceDetector.loadFromDisk(MODELS_DIR),
      faceapi.nets.faceLandmark68Net.loadFromDisk(MODELS_DIR),
      faceapi.nets.faceRecognitionNet.loadFromDisk(MODELS_DIR),
    ])
      .then(() => undefined)
      .catch((err) => {
        modelsLoaded = null;
        throw err;
      });
  }
  return modelsLoaded;
}

export class NoFaceDetectedError extends Error {
  constructor() {
    super("no_face_detected");
    this.name = "NoFaceDetectedError";
  }
}

/**
 * Detects the largest face in the image and returns its 128-d descriptor.
 * Throws NoFaceDetectedError if no face is found — callers decide how to
 * surface that (never silently return a zero vector, which would look like
 * a false "match" against anything).
 */
export async function computeFaceDescriptor(input: ImageInput): Promise<Float32Array> {
  await ensureModelsLoaded();

  const image = await toImage(input);
  const canvas = createCanvas(image.width, image.height);
  const ctx = canvas.getContext("2d");
  ctx.drawImage(image, 0, 0);

  const detection = await faceapi
    // Reason: detectSingleFace's declared parameter type is a browser
    // HTMLCanvasElement, not node-canvas's Canvas — the monkeyPatch above makes
    // node-canvas's Canvas the real runtime implementation, but tsc only sees
    // the declared DOM type, so the cast is needed to bridge the two.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    .detectSingleFace(canvas as any, new faceapi.TinyFaceDetectorOptions())
    .withFaceLandmarks()
    .withFaceDescriptor();

  if (!detection) {
    throw new NoFaceDetectedError();
  }

  return detection.descriptor;
}

// face-api.js already exports this (same sum-of-squared-differences + sqrt,
// same length-mismatch guard) — re-exporting instead of hand-rolling a second
// copy that could silently drift from what the rest of the library assumes.
export const euclideanDistance = faceapi.euclideanDistance;

/** Monotonic 0-1 display score from a distance — NOT what match/no-match decisions
 * are based on (that's MATCH_DISTANCE_THRESHOLD on the raw distance). */
export function similarityFromDistance(distance: number): number {
  return 1 / (1 + distance);
}
