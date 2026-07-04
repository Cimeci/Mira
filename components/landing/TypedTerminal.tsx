"use client";

import { useEffect, useState } from "react";

const PHRASES = [
  "collects evidence",
  "contacts platforms",
  "files reports",
  "takes down abuse",
  "watches for reuploads",
];

/**
 * Terminal explainer: `> MIRA <phrase>` where each phrase types in, holds,
 * deletes, and the next follows — with a blinking block cursor.
 */
export function TypedTerminal() {
  const [typed, setTyped] = useState("");

  useEffect(() => {
    let phrase = 0;
    let pos = 0;
    let dir = 1;
    let timer: ReturnType<typeof setTimeout>;

    const tick = () => {
      let delay = 90;
      pos += dir;
      setTyped(PHRASES[phrase].slice(0, pos));
      if (dir === 1 && pos >= PHRASES[phrase].length) {
        dir = -1;
        delay = 1600;
      } else if (dir === -1 && pos <= 0) {
        dir = 1;
        phrase = (phrase + 1) % PHRASES.length;
        delay = 350;
      } else if (dir === -1) {
        delay = 28;
      }
      timer = setTimeout(tick, delay);
    };

    timer = setTimeout(tick, 600);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="mt-[26px] flex h-6 items-center justify-center gap-[10px] text-[17px] text-mira-luminance">
      <span className="text-mira-electric-lilac">&gt;</span>
      <span className="text-mira-lilac-glow">MIRA</span>
      <span>
        {typed}
        <span className="ml-[3px] inline-block h-4 w-[9px] -translate-y-[2px] animate-blink bg-mira-electric-lilac align-baseline shadow-[0_0_8px_rgba(181,107,255,0.45)]" />
      </span>
    </div>
  );
}
