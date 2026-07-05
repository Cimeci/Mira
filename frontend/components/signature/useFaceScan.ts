"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { prefersReducedMotion } from "@/lib/useReducedMotion";

export type ScanPhase =
  | "closed"
  | "requesting"
  | "denied"
  | "position"
  | "sweep"
  | "frozen"
  | "processing"
  | "done";

/**
 * Why the "denied" screen is showing — drives the message + guidance so the
 * user knows whether to re-allow the permission, switch to a secure URL, or
 * change browser. Empty string means "not denied".
 */
export type DenyReason = "" | "denied" | "insecure" | "unsupported";

/**
 * Deterministic demo switch for a machine with no webcam (projector, judging
 * booth). Set NEXT_PUBLIC_FACE_DEMO=1 to force the scan to play its scripted
 * animation without ever calling getUserMedia — the auto-fallback below only
 * catches sandboxed iframes, not "no camera hardware".
 */
const FORCE_DEMO = process.env.NEXT_PUBLIC_FACE_DEMO === "1";

const TICK_COUNT = 48;
const PROC_BLOCKS = 20;
const PROC_STATUS = [
  "extracting facial features…",
  "computing signature vector…",
  "discarding raw frames…",
  "encrypting signature…",
];

/**
 * The KYC-style face-scan state machine. Faithfully ports the prototype:
 * permission → position (auto face-found + frontal capture) → 360° sweep with
 * the 48-tick enrollment ring → freeze → on-device processing → done.
 *
 * Privacy: frames live only in an in-memory canvas array; nothing is uploaded.
 * The stream is stopped on cancel, error, completion, and unmount. When the
 * camera is blocked (e.g. sandboxed preview), it falls back to demo mode.
 */
export function useFaceScan(onComplete: () => void) {
  const [phase, setPhase] = useState<ScanPhase>("closed");
  const [modalIn, setModalIn] = useState(false);
  const [flash, setFlash] = useState(false);
  const [facePulse, setFacePulse] = useState(false);
  const [glowSweep, setGlowSweep] = useState(false);
  const [sweepProg, setSweepProg] = useState(0);
  const [proc, setProc] = useState(0);
  const [procStage, setProcStage] = useState(0);
  const [demo, setDemo] = useState(false);
  const [frozenSrc, setFrozenSrc] = useState("");
  const [denyReason, setDenyReason] = useState<DenyReason>("");

  const video = useRef<HTMLVideoElement | null>(null);
  const frozenImg = useRef<HTMLImageElement | null>(null);
  const modal = useRef<HTMLDivElement | null>(null);
  const trigger = useRef<HTMLElement | null>(null);

  const stream = useRef<MediaStream | null>(null);
  const frames = useRef<HTMLCanvasElement[]>([]);
  const tickOffsets = useRef<number[]>([]);
  const reduced = useRef(false);
  const timers = useRef<{
    pos?: ReturnType<typeof setTimeout>;
    sweep?: ReturnType<typeof setInterval>;
    cap?: ReturnType<typeof setInterval>;
    processing?: ReturnType<typeof setInterval>;
  }>({});
  const escHandler = useRef<((e: KeyboardEvent) => void) | null>(null);
  const completeRef = useRef(onComplete);
  completeRef.current = onComplete;

  const captureFrame = useCallback(() => {
    if (demo) return;
    const v = video.current;
    if (!v || !v.videoWidth) return;
    const c = document.createElement("canvas");
    c.width = v.videoWidth;
    c.height = v.videoHeight;
    c.getContext("2d")?.drawImage(v, 0, 0);
    frames.current.push(c);
  }, [demo]);

  const stopCapture = useCallback(() => {
    clearTimeout(timers.current.pos);
    clearInterval(timers.current.sweep);
    clearInterval(timers.current.cap);
    clearInterval(timers.current.processing);
    if (escHandler.current) {
      document.removeEventListener("keydown", escHandler.current);
      escHandler.current = null;
    }
    frames.current = [];
    if (stream.current) {
      stream.current.getTracks().forEach((t) => t.stop());
      stream.current = null;
    }
  }, []);

  const close = useCallback(
    (finished?: boolean) => {
      stopCapture();
      setPhase("closed");
      setModalIn(false);
      setFlash(false);
      setGlowSweep(false);
      setFacePulse(false);
      setFrozenSrc("");
      if (finished !== true) trigger.current?.focus();
    },
    [stopCapture]
  );

  const startProcessing = useCallback(() => {
    frames.current = [];
    setPhase("processing");
    setProc(0);
    setProcStage(0);
    const start = Date.now();
    timers.current.processing = setInterval(() => {
      const t = Math.min((Date.now() - start) / 5000, 1);
      setProc(t);
      setProcStage(Math.min(3, Math.floor(t * 4)));
      if (t >= 1) {
        clearInterval(timers.current.processing);
        setPhase("done");
        setTimeout(() => {
          close(true);
          completeRef.current();
        }, 600);
      }
    }, 120);
  }, [close]);

  const finishSweep = useCallback(() => {
    const last = frames.current[frames.current.length - 1];
    const src = demo ? "" : last ? last.toDataURL("image/png") : "";
    const proceed = () => {
      if (stream.current) {
        stream.current.getTracks().forEach((t) => t.stop());
        stream.current = null;
      }
      if (frozenImg.current && src) frozenImg.current.src = src;
      setFrozenSrc(src);
      setPhase("frozen");
      timers.current.pos = setTimeout(() => startProcessing(), 700);
    };
    if (reduced.current) {
      proceed();
      return;
    }
    setGlowSweep(true);
    setTimeout(() => {
      setGlowSweep(false);
      proceed();
    }, 700);
  }, [demo, startProcessing]);

  const beginSweep = useCallback(() => {
    tickOffsets.current = Array.from(
      { length: TICK_COUNT },
      () => Math.random() * 0.045
    );
    setPhase("sweep");
    setSweepProg(0);
    const duration = 8000;
    const start = Date.now();
    timers.current.cap = setInterval(() => captureFrame(), 250);
    timers.current.sweep = setInterval(() => {
      const raw = Math.min((Date.now() - start) / duration, 1);
      const eased = 1 - Math.pow(1 - raw, 1.4);
      setSweepProg(raw >= 1 ? 1.1 : eased);
      if (raw >= 1) {
        clearInterval(timers.current.sweep);
        clearInterval(timers.current.cap);
        finishSweep();
      }
    }, 80);
  }, [captureFrame, finishSweep]);

  const beginPosition = useCallback(() => {
    setPhase("position");
    timers.current.pos = setTimeout(() => {
      captureFrame();
      setFlash(true);
      setFacePulse(true);
      setTimeout(() => setFlash(false), 100);
      timers.current.pos = setTimeout(() => {
        setFacePulse(false);
        beginSweep();
      }, 600);
    }, 1500);
  }, [captureFrame, beginSweep]);

  const startCamera = useCallback(async () => {
    setPhase("requesting");
    setDenyReason("");
    if (FORCE_DEMO) {
      setDemo(true);
      beginPosition();
      return;
    }
    // getUserMedia only exists on a secure context (https or localhost/
    // 127.0.0.1). Reaching the dev server through a LAN IP over http leaves
    // navigator.mediaDevices undefined, so the browser NEVER prompts — surface
    // that explicitly instead of a misleading "access denied".
    const media =
      typeof navigator !== "undefined" ? navigator.mediaDevices : undefined;
    if (!media || typeof media.getUserMedia !== "function") {
      const secure =
        typeof window !== "undefined" && window.isSecureContext;
      setDenyReason(secure ? "unsupported" : "insecure");
      setPhase("denied");
      return;
    }
    try {
      const s = await media.getUserMedia({ video: { facingMode: "user" } });
      stream.current = s;
      setDemo(false);
      if (video.current) video.current.srcObject = s;
      beginPosition();
    } catch (err) {
      const name = err instanceof DOMException ? err.name : "";
      // No camera hardware (projector/booth) or the device is busy: play the
      // scripted demo so the flow always completes. A real permission refusal
      // (NotAllowedError / SecurityError) stays on the actionable "denied"
      // screen — that's the one the user is expected to allow live.
      if (
        name === "NotFoundError" ||
        name === "OverconstrainedError" ||
        name === "NotReadableError"
      ) {
        setDemo(true);
        beginPosition();
        return;
      }
      setDenyReason("denied");
      setPhase("denied");
    }
  }, [beginPosition]);

  const open = useCallback(
    (triggerEl?: HTMLElement | null) => {
      if (triggerEl) trigger.current = triggerEl;
      reduced.current = prefersReducedMotion();
      frames.current = [];
      setPhase("requesting");
      setDenyReason("");
      setModalIn(false);
      setSweepProg(0);
      setProc(0);
      setProcStage(0);
      setFrozenSrc("");
      setFlash(false);
      setGlowSweep(false);
      setFacePulse(false);
      setTimeout(() => setModalIn(true), 20);
      const handler = (e: KeyboardEvent) => {
        if (e.key === "Escape") close();
        if (e.key === "Tab" && modal.current) {
          e.preventDefault();
          modal.current.focus();
        }
      };
      escHandler.current = handler;
      document.addEventListener("keydown", handler);
      startCamera();
    },
    [close, startCamera]
  );

  useEffect(() => stopCapture, [stopCapture]);

  // focus the modal when it mounts
  const setModalRef = useCallback((el: HTMLDivElement | null) => {
    modal.current = el;
    if (el) el.focus();
  }, []);
  const setVideoRef = useCallback((el: HTMLVideoElement | null) => {
    video.current = el;
    if (el && stream.current) el.srcObject = stream.current;
  }, []);
  const setFrozenRef = useCallback((el: HTMLImageElement | null) => {
    frozenImg.current = el;
    if (el && frozenSrc) el.src = frozenSrc;
  }, [frozenSrc]);

  const derived = useMemo(() => {
    const litProg = ["frozen", "processing", "done"].includes(phase)
      ? 1.1
      : phase === "sweep"
        ? sweepProg
        : 0;
    let litCount = 0;
    const offsets = tickOffsets.current;
    const ticks = Array.from({ length: TICK_COUNT }, (_, i) => {
      const lit = litProg >= Math.min(i / TICK_COUNT + (offsets[i] || 0), 1);
      if (lit) litCount++;
      const bright = glowSweep;
      return {
        transform: `rotate(${i * 7.5}deg) translateY(-172px)`,
        bg: lit
          ? bright
            ? "#F2E6FF"
            : "#B56BFF"
          : "rgba(181,107,255,0.18)",
        glow: lit
          ? bright
            ? "0 0 14px rgba(215,179,255,0.95), 0 0 26px rgba(181,107,255,0.8)"
            : "0 0 8px rgba(181,107,255,0.7)"
          : "none",
      };
    });

    const instruction =
      (
        {
          requesting: "requesting camera access…",
          denied: "",
          position: "position your face inside the circle",
          sweep: "slowly move your head in a circle",
          frozen: "scan complete",
          processing: PROC_STATUS[procStage],
        } as Record<string, string>
      )[phase] || "";

    // Message shown inside the lens when we land on "denied", tailored to the
    // real cause so the user knows the actual next step.
    const deniedMessage =
      denyReason === "insecure"
        ? "the camera needs a secure connection. open this page on http://localhost:3000 — not the ip address — or over https."
        : denyReason === "unsupported"
          ? "this browser can't reach the camera. try chrome or safari on a secure (https / localhost) connection."
          : "camera access was blocked. click the camera icon in your browser's address bar to allow it, then try again. nothing is uploaded.";

    const demoLive = demo && ["position", "sweep", "frozen"].includes(phase);

    const procBlocks = Array.from({ length: PROC_BLOCKS }, (_, i) => {
      const lit = i < Math.floor(proc * PROC_BLOCKS);
      return {
        bg: lit ? "#B56BFF" : "rgba(181,107,255,0.15)",
        glow: lit ? "0 0 8px rgba(181,107,255,0.6)" : "none",
      };
    });

    return {
      ticks,
      litCount,
      instruction,
      deniedMessage,
      procBlocks,
      demoLive,
      modalTitle: ["processing", "done"].includes(phase)
        ? "creating your private facial signature"
        : "scan your face",
      show: {
        modal: phase !== "closed",
        lens: ["requesting", "denied", "position", "sweep", "frozen"].includes(
          phase
        ),
        video: !demo && ["position", "sweep"].includes(phase),
        frozen: !demo && phase === "frozen" && !!frozenSrc,
        eye: phase === "requesting" || demoLive,
        denied: phase === "denied",
        tryAgain: phase === "denied",
        oval: phase === "position",
        counter: phase === "sweep",
        procArea: ["processing", "done"].includes(phase),
        procRun: phase === "processing",
        procDone: phase === "done",
      },
      lensRing: facePulse
        ? "0 0 0 3px rgba(140,255,190,0.5), 0 0 24px rgba(181,107,255,0.8)"
        : "0 0 18px rgba(107,47,165,0.35)",
    };
  }, [
    phase,
    sweepProg,
    glowSweep,
    procStage,
    proc,
    demo,
    facePulse,
    frozenSrc,
    denyReason,
  ]);

  return {
    phase,
    modalIn,
    flash,
    frozenSrc,
    derived,
    open,
    cancel: () => close(),
    retry: startCamera,
    refs: { setModalRef, setVideoRef, setFrozenRef },
  };
}
