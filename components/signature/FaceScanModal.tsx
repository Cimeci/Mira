"use client";

import Image from "next/image";
import type { useFaceScan } from "./useFaceScan";

type Scan = ReturnType<typeof useFaceScan>;

/** Fullscreen KYC face-scan modal. Purely presentational — driven by useFaceScan. */
export function FaceScanModal({ scan }: { scan: Scan }) {
  const { phase, modalIn, flash, derived, refs, cancel, retry } = scan;
  const { show, ticks, litCount, instruction, procBlocks, modalTitle, lensRing } =
    derived;

  if (!show.modal) return null;

  return (
    <div
      onClick={cancel}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-[rgba(6,4,10,0.85)] font-mono text-mira-luminance [backdrop-filter:blur(5px)]"
    >
      <div
        ref={refs.setModalRef}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={modalTitle}
        tabIndex={-1}
        className="flex flex-col items-center gap-[18px] rounded-panel border border-[rgba(181,107,255,0.4)] bg-mira-void px-8 pb-7 pt-10 outline-none transition-[transform,opacity] duration-150 sm:px-16"
        style={{
          transform: modalIn ? "scale(1)" : "scale(0.92)",
          opacity: modalIn ? 1 : 0,
          boxShadow:
            "0 0 0 1px rgba(181,107,255,0.25), 0 0 40px rgba(107,47,165,0.4)",
        }}
      >
        <div className="text-shadow-title max-w-[420px] text-center font-display text-section leading-[1.3] text-mira-lilac-glow">
          {modalTitle}
        </div>

        {show.lens && (
          <div className="relative flex h-[372px] w-[372px] items-center justify-center">
            {ticks.map((t, i) => (
              <div
                key={i}
                className="absolute left-1/2 top-1/2 -ml-[1.5px] -mt-[7px] h-[14px] w-[3px] rounded-[2px]"
                style={{
                  background: t.bg,
                  boxShadow: t.glow,
                  transform: t.transform,
                }}
              />
            ))}
            <div
              className="relative flex h-[296px] w-[296px] items-center justify-center overflow-hidden rounded-full border border-[rgba(181,107,255,0.45)] bg-mira-night"
              style={{ boxShadow: lensRing }}
            >
              <video
                ref={refs.setVideoRef}
                autoPlay
                playsInline
                muted
                className="absolute inset-0 h-full w-full -scale-x-100 object-cover"
                style={{ display: show.video ? "block" : "none" }}
              />
              {/* frozen frame src is assigned imperatively from the camera */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                ref={refs.setFrozenRef}
                alt=""
                className="absolute inset-0 h-full w-full -scale-x-100 object-cover"
                style={{ display: show.frozen ? "block" : "none" }}
              />
              {show.eye && (
                <div className="flex animate-softpulse flex-col items-center">
                  <Image
                    src="/assets/logo_eye.png"
                    alt=""
                    width={110}
                    height={70}
                    className="block w-[110px] [filter:drop-shadow(0_0_12px_rgba(181,107,255,0.5))]"
                  />
                </div>
              )}
              {show.denied && (
                <div className="px-9 text-center text-caption leading-[1.5] text-mira-muted-text">
                  camera access is needed. nothing is uploaded.
                </div>
              )}
              {show.oval && (
                <div className="pointer-events-none absolute left-1/2 top-1/2 -ml-[65px] -mt-[85px] h-[170px] w-[130px] rounded-[50%] border-2 border-dashed border-[rgba(215,179,255,0.65)]" />
              )}
              <div className="pointer-events-none absolute inset-0 [background:repeating-linear-gradient(to_bottom,rgba(242,230,255,0.05)_0px,rgba(242,230,255,0.05)_1px,transparent_2px,transparent_5px)]" />
              {flash && (
                <div className="absolute inset-0 bg-[rgba(255,255,255,0.85)]" />
              )}
            </div>
          </div>
        )}

        {show.procArea && (
          <div className="flex min-h-[250px] flex-col items-center justify-center gap-[18px]">
            {show.procRun && (
              <div className="flex flex-col items-center gap-4">
                <div className="flex h-[130px] w-[130px] items-center justify-center rounded-full border border-dashed border-[rgba(181,107,255,0.5)] bg-mira-night">
                  <Image
                    src="/assets/logo_eye.png"
                    alt=""
                    width={64}
                    height={40}
                    className="block w-16 animate-softpulse [filter:drop-shadow(0_0_10px_rgba(181,107,255,0.5))]"
                  />
                </div>
                <div className="max-w-[320px] text-center text-caption leading-[1.5] text-mira-muted-text">
                  processing happens on your device. the raw images are
                  discarded.
                </div>
                <div className="flex gap-[3px]">
                  {procBlocks.map((b, i) => (
                    <div
                      key={i}
                      className="h-4 w-[11px]"
                      style={{ background: b.bg, boxShadow: b.glow }}
                    />
                  ))}
                </div>
              </div>
            )}
            {show.procDone && (
              <div className="font-display text-[16px] text-mira-lilac-glow [text-shadow:0_0_4px_rgba(242,230,255,0.9),0_0_16px_rgba(181,107,255,0.8)]">
                facial signature created ✓
              </div>
            )}
          </div>
        )}

        <div
          aria-live="polite"
          className="min-h-5 text-center text-body-sm text-mira-lilac-glow"
        >
          {instruction}
        </div>
        {show.counter && (
          <div className="text-caption text-mira-muted-text [font-variant-numeric:tabular-nums]">
            scanning… {litCount}/48
          </div>
        )}
        {show.tryAgain && (
          <button
            type="button"
            onClick={retry}
            className="mira-clip flex min-h-[40px] items-center border border-mira-electric-lilac bg-mira-night px-[26px] font-display text-label uppercase tracking-label text-mira-lilac-glow transition-colors hover:bg-mira-purple-steel hover:text-mira-luminance"
          >
            try again
          </button>
        )}
        <button
          type="button"
          onClick={cancel}
          className="px-[10px] py-1 text-caption tracking-label text-mira-muted-dim transition-colors hover:text-mira-lilac-glow"
        >
          cancel
        </button>
      </div>
    </div>
  );
}
