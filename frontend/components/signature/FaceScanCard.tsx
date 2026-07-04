"use client";

import Image from "next/image";
import { useRef } from "react";

const STEPS = [
  "take a live picture",
  "create your private facial signature",
  "use it to verify possible abusive copies",
  "verify matches before action is taken",
];

/** Static facial-signature card: lens placeholder, CTA, steps, privacy note. */
export function FaceScanCard({ onScan }: { onScan: (el: HTMLElement) => void }) {
  const btnRef = useRef<HTMLButtonElement>(null);

  return (
    <div className="flex flex-col items-start gap-11 rounded-card border border-[rgba(181,107,255,0.4)] bg-mira-night p-7 shadow-[0_0_18px_rgba(107,47,165,0.18)] md:flex-row">
      <div className="flex flex-shrink-0 flex-col items-center gap-4 self-center md:self-start">
        <div className="relative flex h-[200px] w-[200px] flex-col items-center justify-center gap-2 overflow-hidden rounded-full border border-dashed border-[rgba(181,107,255,0.55)] bg-mira-void">
          <div className="pointer-events-none absolute inset-0 [background:repeating-linear-gradient(to_bottom,rgba(242,230,255,0.05)_0px,rgba(242,230,255,0.05)_1px,transparent_2px,transparent_5px)]" />
          <Image
            src="/assets/logo_eye.png"
            alt=""
            width={96}
            height={60}
            className="block w-24 [filter:drop-shadow(0_0_12px_rgba(181,107,255,0.5))]"
          />
          <div className="text-caption uppercase tracking-label text-mira-muted-dim">
            live camera
          </div>
        </div>
        <button
          ref={btnRef}
          type="button"
          onClick={() => btnRef.current && onScan(btnRef.current)}
          className="mira-clip mira-cta-flow text-shadow-glow flex min-h-[48px] items-center border border-mira-electric-lilac px-8 font-display text-label uppercase tracking-label text-mira-luminance shadow-[0_0_0_1px_rgba(181,107,255,0.9),0_0_12px_rgba(181,107,255,0.55),0_0_26px_rgba(107,47,165,0.45)] hover:border-mira-lilac-glow"
        >
          take live picture
        </button>
      </div>

      <div className="flex flex-col gap-[18px]">
        <div className="text-[14px] leading-[1.55] text-mira-muted-text">
          one live picture, four steps, nothing uploaded.
        </div>
        <div className="flex flex-col gap-3 text-[14px] text-mira-luminance">
          {STEPS.map((step, i) => (
            <div key={step} className="flex items-baseline gap-[14px]">
              <span className="font-display text-label text-mira-electric-lilac">
                {String(i + 1).padStart(2, "0")}
              </span>{" "}
              {step}
            </div>
          ))}
        </div>
        <div className="flex items-start gap-3 rounded-chip border border-[rgba(181,107,255,0.3)] bg-mira-void px-4 py-[14px] text-caption leading-[1.55] text-mira-muted-text">
          <span className="text-mira-lilac-glow">◆</span>
          <span>
            your facial signature is used only to find and verify abusive copies.
            it is never shared with platforms unless required for your case and
            approved by you. the raw image stays on your device.
          </span>
        </div>
      </div>
    </div>
  );
}
