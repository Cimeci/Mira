"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { prefersReducedMotion } from "./useReducedMotion";

interface CounterState {
  value: number;
  pulsing: boolean;
}

/**
 * Staggered count-up for the landing impact counters.
 * - triggers once on `start()` (wired to an IntersectionObserver)
 * - each counter animates 0→target over ~1.6s ease-out via rAF
 * - staggered 150ms apart, tabular-nums handled by the view
 * - one-frame glow pulse on landing
 * - reduced-motion: snap to final values, no animation, no pulse
 */
export function useCountUp(targets: number[]) {
  const [states, setStates] = useState<CounterState[]>(() =>
    targets.map(() => ({ value: 0, pulsing: false }))
  );
  const started = useRef(false);
  const rafs = useRef<number[]>([]);
  const timeouts = useRef<ReturnType<typeof setTimeout>[]>([]);

  const start = useCallback(() => {
    if (started.current) return;
    started.current = true;

    if (prefersReducedMotion()) {
      setStates(targets.map((t) => ({ value: t, pulsing: false })));
      return;
    }

    const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);

    targets.forEach((target, i) => {
      const startTimeout = setTimeout(() => {
        const duration = 1600;
        let startTs: number | null = null;

        const step = (ts: number) => {
          if (startTs === null) startTs = ts;
          const t = Math.min((ts - startTs) / duration, 1);
          const v = Math.round(easeOut(t) * target);
          setStates((prev) => {
            const next = prev.slice();
            next[i] = { ...next[i], value: v };
            return next;
          });
          if (t < 1) {
            rafs.current[i] = requestAnimationFrame(step);
          } else {
            setStates((prev) => {
              const next = prev.slice();
              next[i] = { ...next[i], pulsing: true };
              return next;
            });
            const off = setTimeout(() => {
              setStates((prev) => {
                const next = prev.slice();
                next[i] = { ...next[i], pulsing: false };
                return next;
              });
            }, 180);
            timeouts.current.push(off);
          }
        };
        rafs.current[i] = requestAnimationFrame(step);
      }, i * 150);
      timeouts.current.push(startTimeout);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    return () => {
      rafs.current.forEach((r) => cancelAnimationFrame(r));
      timeouts.current.forEach((t) => clearTimeout(t));
    };
  }, []);

  return { states, start };
}
