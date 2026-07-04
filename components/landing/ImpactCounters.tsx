"use client";

import { Fragment, useEffect, useRef } from "react";
import { useCountUp } from "@/lib/useCountUp";

const COUNTERS = [
  { target: 154, label: "cases opened" },
  { target: 1208, label: "takedowns completed" },
  { target: 763, label: "reuploads caught" },
];

const BASE_GLOW =
  "0 0 4px rgba(242,230,255,0.6), 0 0 10px rgba(181,107,255,0.5)";
const PULSE_GLOW =
  "0 0 6px rgba(242,230,255,0.9), 0 0 18px rgba(215,179,255,0.55), 0 0 32px rgba(181,107,255,0.6)";

/** Proof/impact panel: three counters that count up on scroll into view. */
export function ImpactCounters() {
  const { states, start } = useCountUp(COUNTERS.map((c) => c.target));
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          start();
          io.disconnect();
        }
      },
      { threshold: 0.4 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [start]);

  return (
    <div
      ref={ref}
      className="mt-16 flex flex-wrap items-stretch justify-center rounded-card border border-[rgba(181,107,255,0.35)] bg-mira-night px-[10px] py-[22px] shadow-panel"
    >
      {COUNTERS.map((c, i) => (
        <Fragment key={c.label}>
          <div className="flex min-w-[150px] flex-col items-center gap-[6px] px-9">
            <div
              className="font-display text-[34px] leading-none text-mira-lilac-glow [font-variant-numeric:tabular-nums]"
              style={{ textShadow: states[i].pulsing ? PULSE_GLOW : BASE_GLOW }}
            >
              {states[i].value.toLocaleString("en-US")}
            </div>
            <div className="text-label uppercase tracking-label text-mira-muted-text">
              {c.label}
            </div>
          </div>
          {i < COUNTERS.length - 1 && (
            <div className="hidden w-px self-stretch bg-[rgba(181,107,255,0.25)] sm:block" />
          )}
        </Fragment>
      ))}
    </div>
  );
}
