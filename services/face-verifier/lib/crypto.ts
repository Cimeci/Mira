import { createCipheriv, createDecipheriv, randomBytes } from "node:crypto";

// G-5 « chiffrer ce qui est retenu » : tout ce que store.ts écrit sur disque passe
// par ce module — AES-256-GCM, clé via EVIDENCE_ENCRYPTION_KEY (base64, 32 octets,
// jamais commitée ; placeholder dans .env.example à la racine du repo).
//
// Sans clé configurée : clé aléatoire par process. Le stockage vit déjà dans un
// /tmp éphémère (voir store.ts) — perdre la clé au restart ne perd rien que le
// filesystem n'aurait pas déjà perdu. La garantie tenue dans TOUS les cas :
// aucun embedding biométrique ni evidence en clair sur le disque.

const ALGORITHM = "aes-256-gcm";
const KEY_BYTES = 32;
const IV_BYTES = 12;

export class DecryptError extends Error {
  constructor(cause?: unknown) {
    super("decrypt_failed");
    this.name = "DecryptError";
    this.cause = cause;
  }
}

interface EncryptedEnvelope {
  alg: typeof ALGORITHM;
  iv: string;
  tag: string;
  data: string;
}

function isEncryptedEnvelope(value: unknown): value is EncryptedEnvelope {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    v.alg === ALGORITHM &&
    typeof v.iv === "string" &&
    typeof v.tag === "string" &&
    typeof v.data === "string"
  );
}

let cachedKey: Buffer | null = null;

function encryptionKey(): Buffer {
  if (cachedKey) return cachedKey;
  const fromEnv = process.env.EVIDENCE_ENCRYPTION_KEY;
  if (fromEnv) {
    const key = Buffer.from(fromEnv, "base64");
    if (key.byteLength !== KEY_BYTES) {
      // Fail fast : retomber silencieusement sur une clé aléatoire rendrait tout
      // illisible au prochain process sans que personne ne comprenne pourquoi.
      throw new Error(`EVIDENCE_ENCRYPTION_KEY must be ${KEY_BYTES} bytes, base64-encoded`);
    }
    cachedKey = key;
  } else {
    cachedKey = randomBytes(KEY_BYTES);
  }
  return cachedKey;
}

/** Sérialise puis chiffre une valeur JSON-able en enveloppe prête pour writeFile. */
export function encryptJson(value: unknown): string {
  const iv = randomBytes(IV_BYTES);
  const cipher = createCipheriv(ALGORITHM, encryptionKey(), iv);
  const data = Buffer.concat([cipher.update(JSON.stringify(value), "utf-8"), cipher.final()]);
  const envelope: EncryptedEnvelope = {
    alg: ALGORITHM,
    iv: iv.toString("base64"),
    tag: cipher.getAuthTag().toString("base64"),
    data: data.toString("base64"),
  };
  return JSON.stringify(envelope);
}

/**
 * Déchiffre une enveloppe produite par encryptJson. Lève DecryptError pour tout
 * contenu indéchiffrable avec la clé courante : enveloppe altérée/tronquée, ou
 * fichier écrit par un process précédent sous clé éphémère.
 */
export function decryptJson<T>(raw: string): T {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    throw new DecryptError(err);
  }
  if (!isEncryptedEnvelope(parsed)) throw new DecryptError();
  try {
    const decipher = createDecipheriv(ALGORITHM, encryptionKey(), Buffer.from(parsed.iv, "base64"));
    decipher.setAuthTag(Buffer.from(parsed.tag, "base64"));
    const plain = Buffer.concat([
      decipher.update(Buffer.from(parsed.data, "base64")),
      decipher.final(),
    ]);
    return JSON.parse(plain.toString("utf-8")) as T;
  } catch (err) {
    throw new DecryptError(err);
  }
}

/** Seam de test : oublie la clé cachée pour que le prochain appel relise l'env
 * (ou régénère une clé éphémère). Jamais appelé par le code de production. */
export function resetKeyForTests(): void {
  cachedKey = null;
}
