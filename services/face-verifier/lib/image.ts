import { type Image, loadImage } from "canvas";

export type ImageInput = Buffer | Image;

/**
 * Decodes a Buffer into an Image, or passes an already-decoded Image straight
 * through. Lets a caller that needs multiple operations on the same source
 * bytes (e.g. both a perceptual hash and a face descriptor) decode once and
 * share the result, instead of each operation decoding independently.
 */
export async function toImage(input: ImageInput): Promise<Image> {
  if (Buffer.isBuffer(input)) {
    return loadImage(input);
  }
  return input;
}
