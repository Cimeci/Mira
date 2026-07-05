"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type UIEvent,
} from "react";
import { useRouter } from "next/navigation";
import { useFlow } from "@/lib/flow-context";
import { prefersReducedMotion } from "@/lib/useReducedMotion";
import { ScreenTitle } from "@/components/ui/ScreenTitle";
import { BackButton } from "@/components/ui/BackButton";
import { cn } from "@/lib/cn";

function formatStamp(now: Date): string {
  const date = now
    .toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    })
    .toLowerCase();
  const time = now.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
  });
  return `${date}, ${time}`;
}

export function MandateSigning() {
  const router = useRouter();
  const { signMandate } = useFlow();

  const [docScrolled, setDocScrolled] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [hasStrokes, setHasStrokes] = useState(false);
  const [signed, setSigned] = useState(false);
  const [stamp, setStamp] = useState("");
  const [docGlow, setDocGlow] = useState(false);
  const [today] = useState(() =>
    new Date()
      .toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      })
      .toLowerCase()
  );

  const padRef = useRef<HTMLCanvasElement>(null);
  const docSigRef = useRef<HTMLCanvasElement>(null);
  const padCtx = useRef<CanvasRenderingContext2D | null>(null);
  const docCtx = useRef<CanvasRenderingContext2D | null>(null);
  const drawing = useRef(false);
  const scale = useRef({ x: 1, y: 1 });

  const ensurePad = useCallback(() => {
    const el = padRef.current;
    if (!el) return;
    const w = el.clientWidth || 330;
    const h = el.clientHeight || 170;
    if (el.width !== Math.round(w * 2) || !padCtx.current) {
      el.width = w * 2;
      el.height = h * 2;
      const ctx = el.getContext("2d");
      if (!ctx) return;
      ctx.scale(2, 2);
      ctx.lineWidth = 2.2;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.strokeStyle = "#D7B3FF";
      ctx.shadowColor = "rgba(181,107,255,0.8)";
      ctx.shadowBlur = 4;
      padCtx.current = ctx;
    }
  }, []);

  const ensureDoc = useCallback(() => {
    const el = docSigRef.current;
    const pad = padRef.current;
    if (!el || !pad) return;
    const w = el.clientWidth || 300;
    const h = el.clientHeight || 64;
    if (el.width !== Math.round(w * 2) || !docCtx.current) {
      el.width = w * 2;
      el.height = h * 2;
      const ctx = el.getContext("2d");
      if (!ctx) return;
      ctx.scale(2, 2);
      ctx.lineWidth = 1.4;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.strokeStyle = "#241A2E";
      docCtx.current = ctx;
    }
    scale.current = {
      x: w / (pad.clientWidth || 330),
      y: h / (pad.clientHeight || 170),
    };
  }, []);

  const padPos = (e: ReactPointerEvent<HTMLCanvasElement>): [number, number] => {
    const r = padRef.current!.getBoundingClientRect();
    return [e.clientX - r.left, e.clientY - r.top];
  };

  const onDown = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    if (signed) return;
    ensurePad();
    ensureDoc();
    drawing.current = true;
    try {
      e.currentTarget.setPointerCapture(e.pointerId);
    } catch {
      /* no-op */
    }
    const [x, y] = padPos(e);
    padCtx.current?.beginPath();
    padCtx.current?.moveTo(x, y);
    padCtx.current?.lineTo(x + 0.1, y + 0.1);
    padCtx.current?.stroke();
    if (docCtx.current) {
      const { x: sx, y: sy } = scale.current;
      docCtx.current.beginPath();
      docCtx.current.moveTo(x * sx, y * sy);
      docCtx.current.lineTo(x * sx + 0.1, y * sy + 0.1);
      docCtx.current.stroke();
    }
    if (!hasStrokes) setHasStrokes(true);
  };

  const onMove = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    if (!drawing.current || !padCtx.current) return;
    const [x, y] = padPos(e);
    padCtx.current.lineTo(x, y);
    padCtx.current.stroke();
    if (docCtx.current) {
      const { x: sx, y: sy } = scale.current;
      docCtx.current.lineTo(x * sx, y * sy);
      docCtx.current.stroke();
    }
  };

  const onUp = () => {
    drawing.current = false;
  };

  const clear = () => {
    if (signed) return;
    const pad = padRef.current;
    const doc = docSigRef.current;
    if (pad && padCtx.current) padCtx.current.clearRect(0, 0, pad.width, pad.height);
    if (doc && docCtx.current) docCtx.current.clearRect(0, 0, doc.width, doc.height);
    setHasStrokes(false);
  };

  const onDocScroll = (e: UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    if (!docScrolled && el.scrollTop + el.clientHeight >= el.scrollHeight - 30) {
      setDocScrolled(true);
    }
  };

  const canSign = hasStrokes && agreed && docScrolled && !signed;

  const doSign = () => {
    if (!canSign) return;
    const now = new Date();
    const s = formatStamp(now);
    const reduced = prefersReducedMotion();
    setStamp(s);
    setSigned(true);
    signMandate(s);
    if (!reduced) {
      setDocGlow(true);
      setTimeout(() => setDocGlow(false), 700);
    }
    setTimeout(() => router.push("/signature"), 800);
  };

  // keep canvases sized to their rendered box
  useEffect(() => {
    ensurePad();
    ensureDoc();
  }, [ensurePad, ensureDoc]);

  const reduced = typeof window !== "undefined" && prefersReducedMotion();

  return (
    <div className="flex flex-col gap-[22px]">
      <div>
        <ScreenTitle>sign your mandate</ScreenTitle>
        <p className="mt-[10px] max-w-[660px] text-[14px] leading-[1.6] text-mira-muted-text">
          you authorize mira to act in your name for this case only. you approve
          every step before it is sent. no identity document is required.
        </p>
      </div>

      <div className="flex flex-col items-start gap-[30px] lg:flex-row">
        {/* the contract document */}
        <div className="relative w-full min-w-0 lg:flex-[1.5]">
          <div
            className="rounded-card border border-[rgba(181,107,255,0.55)] bg-mira-night p-[14px] transition-shadow duration-500"
            style={{
              boxShadow: docGlow
                ? "0 0 0 1px rgba(181,107,255,0.9), 0 0 40px rgba(181,107,255,0.6)"
                : "0 0 24px rgba(107,47,165,0.3)",
            }}
          >
            <div
              data-mira-scroll
              onScroll={onDocScroll}
              tabIndex={0}
              aria-label="mandate of representation. scroll to the end to read."
              className="h-[520px] overflow-y-auto outline-none"
            >
              <div className="bg-mira-paper px-12 pb-10 pt-11 font-serif text-[14px] leading-[1.65] text-mira-paper-ink">
                <div className="text-center text-[20px] tracking-[0.1em]">
                  mandate of representation
                </div>
                <div className="mt-[6px] text-center text-[11px] uppercase tracking-[0.14em] text-mira-paper-muted">
                  case mira-4821
                </div>

                <div className="mt-[26px] flex flex-col gap-[6px] border border-[#cfc5b2] px-[18px] py-[14px] font-mono text-caption">
                  <div>
                    <span className="text-mira-paper-muted">principal:</span> the
                    signatory
                  </div>
                  <div>
                    <span className="text-mira-paper-muted">agent:</span> mira
                  </div>
                  <div>
                    <span className="text-mira-paper-muted">scope:</span>{" "}
                    example-site.com · case mira-4821
                  </div>
                  <div>
                    <span className="text-mira-paper-muted">validity:</span> until
                    case closed or revoked
                  </div>
                </div>

                <div className="mt-7 flex flex-col gap-5">
                  {[
                    [
                      "article 1 · access",
                      "mira may access the target url(s) provided by the principal, for the sole purpose of this case.",
                    ],
                    [
                      "article 2 · evidence",
                      "mira may collect and seal evidence from those urls so it can be used in legal proceedings.",
                    ],
                    [
                      "article 3 · reports",
                      "mira may prepare reports to the platform, its hosting provider, and the competent authorities.",
                    ],
                    [
                      "article 4 · approval",
                      "nothing is sent to any party without the principal's explicit approval of each step.",
                    ],
                    [
                      "article 5 · revocation",
                      "the principal may revoke this mandate and request deletion of all related data at any time.",
                    ],
                  ].map(([head, body]) => (
                    <div key={head}>
                      <div className="text-caption uppercase tracking-[0.1em] text-mira-paper-muted">
                        {head}
                      </div>
                      <div className="mt-1">{body}</div>
                    </div>
                  ))}
                </div>

                <div className="relative mt-12 flex items-end justify-between gap-12">
                  <div className="flex-1">
                    <canvas
                      ref={docSigRef}
                      className="block h-16 w-full"
                    />
                    <div className="border-t border-dotted border-mira-paper-ink pt-[6px] text-[10px] uppercase tracking-label text-mira-paper-muted">
                      signature of the principal
                    </div>
                  </div>
                  <div className="w-[140px] flex-shrink-0">
                    <div className="flex h-16 items-end pb-[6px] font-mono text-body-sm">
                      {today}
                    </div>
                    <div className="border-t border-dotted border-mira-paper-ink pt-[6px] text-[10px] uppercase tracking-label text-mira-paper-muted">
                      date
                    </div>
                  </div>
                  {signed && (
                    <div
                      className="absolute right-[150px] top-[-34px] border-2 border-mira-neon-purple bg-[rgba(107,47,165,0.07)] px-3 py-[7px] font-display text-[10px] uppercase tracking-label text-mira-neon-purple"
                      style={{ transform: reduced ? "rotate(0deg)" : "rotate(-5deg)" }}
                    >
                      signed · {stamp} · case mira-4821
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
          <div
            className="pointer-events-none absolute bottom-6 left-1/2 -translate-x-1/2 rounded-full border border-[rgba(181,107,255,0.5)] bg-[rgba(20,14,31,0.92)] px-4 py-[6px] text-caption uppercase tracking-label text-mira-lilac-glow transition-opacity duration-400"
            style={{ opacity: docScrolled ? 0 : 1 }}
          >
            scroll to read ↓
          </div>
        </div>

        {/* the signing panel */}
        <div className="sticky top-6 flex w-full flex-shrink-0 flex-col gap-4 rounded-card border border-[rgba(181,107,255,0.4)] bg-mira-night px-6 py-[22px] shadow-[0_0_18px_rgba(107,47,165,0.18)] lg:w-[380px]">
          <div className="text-shadow-title font-display text-[15px] text-mira-lilac-glow">
            your signature
          </div>

          <label
            className={cn(
              "flex items-start gap-3 text-body-sm leading-[1.5]",
              docScrolled
                ? "cursor-pointer text-mira-muted-text"
                : "cursor-not-allowed text-mira-muted-dim"
            )}
          >
            <input
              type="checkbox"
              checked={agreed}
              disabled={!docScrolled || signed}
              onChange={() => setAgreed((v) => !v)}
              className="mt-[1px] h-4 w-4 accent-mira-electric-lilac"
            />
            <span>
              i have read the mandate and i authorize mira to act in my name
            </span>
          </label>
          {!docScrolled && (
            <div className="-mt-2 text-caption text-mira-muted-dim">
              scroll to the end of the document to enable
            </div>
          )}

          <div className="relative">
            <canvas
              ref={padRef}
              onPointerDown={onDown}
              onPointerMove={onMove}
              onPointerUp={onUp}
              onPointerCancel={onUp}
              className="block h-[170px] w-full cursor-crosshair rounded-chip border-2 border-dashed border-[rgba(181,107,255,0.45)] bg-mira-void [touch-action:none]"
            />
            {!hasStrokes && (
              <div className="pointer-events-none absolute inset-x-0 top-[74px] text-center text-caption tracking-[0.06em] text-mira-muted-dim">
                sign here with your finger or mouse
              </div>
            )}
            <button
              type="button"
              onClick={clear}
              className="absolute bottom-2 right-[10px] px-2 py-1 text-caption uppercase tracking-label text-mira-muted-dim transition-colors hover:text-mira-lilac-glow"
            >
              clear
            </button>
          </div>

          <div className="text-caption leading-[1.5] text-mira-muted-dim">
            your strokes are mirrored into the signature line of the document.
            the signature stays in this session only.
          </div>

          {signed ? (
            <div className="flex items-center justify-center gap-[10px] text-body-sm text-mira-muted-text">
              signed · {stamp} <span className="text-mira-electric-lilac">✓</span>
            </div>
          ) : canSign ? (
            <button
              type="button"
              onClick={doSign}
              className="mira-clip mira-cta-flow text-shadow-glow flex min-h-[48px] items-center justify-center border border-mira-electric-lilac font-display text-label uppercase tracking-label text-mira-luminance shadow-[0_0_0_1px_rgba(181,107,255,0.9),0_0_12px_rgba(181,107,255,0.55),0_0_26px_rgba(107,47,165,0.45)] hover:border-mira-lilac-glow"
            >
              sign mandate
            </button>
          ) : (
            <div className="mira-clip flex min-h-[48px] cursor-not-allowed items-center justify-center border border-[rgba(181,107,255,0.3)] bg-mira-night font-display text-label uppercase tracking-label text-mira-muted-dim opacity-60">
              sign mandate
            </div>
          )}
        </div>
      </div>

      <BackButton href="/actions" className="self-start" />
    </div>
  );
}
