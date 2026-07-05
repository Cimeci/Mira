"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";

/**
 * Live "agent view" for the collect-evidence phase: streams the real
 * Computer-Use crawl of the victim's submitted url and shows the agent's live
 * screen + a running trace of what it does and where it goes. Renders ONLY what
 * the crawl emits — no seeded/placeholder frames or lines.
 *
 * The EventSource hits mira/web directly (cross-origin, CORS-enabled) rather
 * than a Next proxy: the Next dev server buffers a proxied stream to the end,
 * which kills the live view — the direct connection flushes frames as they land.
 *
 * The stream is a one-shot finite job (crawl → done/error), so we never
 * auto-reconnect: closing the EventSource on done/error also stops the native
 * reconnect that would otherwise restart a fresh (costly) crawl.
 */

const CU_STREAM_BASE =
  process.env.NEXT_PUBLIC_CU_STREAM_BASE || "http://localhost:8001";

type TraceTone = "muted" | "think" | "act" | "safety" | "err" | "page";
type Phase = "idle" | "connecting" | "running" | "done" | "failed";

interface TraceLine {
  id: number;
  icon: string;
  text: string;
  tone: TraceTone;
}

/** CU stream event (mira/web /stream). Untrusted shape → read every field defensively. */
interface CuEvent {
  type: string;
  image?: string;
  label?: string;
  text?: string;
  name?: string;
  action?: string;
  args?: string;
  url?: string;
  n?: number;
  total?: number;
  depth?: number;
  new?: number;
  count?: number;
  pages?: number;
  elapsed?: number;
  found?: number;
  queued?: number;
  message?: string;
  limits?: { pages?: number; depth?: number };
}

interface AgentLiveViewProps {
  /** Latches true once for a fresh (not-yet-finished) case — gates the single crawl. */
  run: boolean;
  /** The real url the victim submitted (case scope). Null until known. */
  targetUrl: string | null;
}

const MAX_LINES = 40;

const TONE_CLASS: Record<TraceTone, string> = {
  muted: "text-mira-muted-dim",
  think: "text-mira-lilac-glow",
  act: "text-mira-luminance",
  safety: "text-mira-warn",
  err: "text-mira-danger",
  page: "text-mira-electric-lilac",
};

export function AgentLiveView({ run, targetUrl }: AgentLiveViewProps) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [frame, setFrame] = useState<string | null>(null);
  const [frameLabel, setFrameLabel] = useState("");
  const [lines, setLines] = useState<TraceLine[]>([]);
  const [summary, setSummary] = useState<string | null>(null);

  const lineId = useRef(0);
  const traceRef = useRef<HTMLOListElement | null>(null);

  useEffect(() => {
    // Wait for the real victim url; only ever start one crawl per mount.
    if (!run || !targetUrl) return;

    const addLine = (icon: string, text: string, tone: TraceTone) => {
      lineId.current += 1;
      const line = { id: lineId.current, icon, text, tone };
      setLines((prev) => {
        const next = [...prev, line];
        return next.length > MAX_LINES ? next.slice(next.length - MAX_LINES) : next;
      });
    };

    const es = new EventSource(
      `${CU_STREAM_BASE}/stream?url=${encodeURIComponent(targetUrl)}`
    );
    setPhase("connecting");

    es.onmessage = (e) => {
      let ev: CuEvent;
      try {
        ev = JSON.parse(e.data) as CuEvent;
      } catch {
        return; // keep-alive / non-JSON frame
      }
      switch (ev.type) {
        case "crawl_start":
          setPhase("running");
          addLine("▸", `scanning · up to ${ev.limits?.pages ?? "?"} pages`, "muted");
          break;
        case "page":
          addLine("→", `page ${ev.n}/${ev.total} · ${ev.url ?? ""}`, "page");
          break;
        case "frame":
          if (ev.image) setFrame(ev.image);
          setFrameLabel(ev.label ?? "");
          break;
        case "reasoning":
          if (ev.text) addLine("🧠", ev.text, "think");
          break;
        case "action":
          addLine("🖱", `${ev.name ?? ""} ${ev.args ?? ""}`.trim(), "act");
          break;
        case "safety":
          addLine("🔒", `sensitive: ${ev.action ?? ev.name ?? ""} — ${ev.text ?? ""}`, "safety");
          break;
        case "images":
          addLine("🖼", `+${ev.new} media · ${ev.total} total`, "muted");
          break;
        case "links":
          addLine("🔗", `${ev.found} links · ${ev.queued} queued`, "muted");
          break;
        case "note":
          if (ev.text) addLine("·", ev.text, "muted");
          break;
        case "error":
          addLine("⚠️", ev.message ?? "crawl error", "err");
          setPhase("failed");
          es.close();
          break;
        case "done":
          setSummary(`${ev.count ?? 0} media · ${ev.pages ?? 0} pages · ${ev.elapsed ?? 0}s`);
          setPhase("done");
          es.close();
          break;
      }
    };

    // Finite stream: a drop/end means we're done listening — never reconnect
    // (that would relaunch a full crawl). Only flip to failed if still running.
    es.onerror = () => {
      es.close();
      setPhase((p) => (p === "done" ? p : p === "failed" ? p : "failed"));
    };

    return () => es.close();
  }, [run, targetUrl]);

  // Keep the newest trace line in view.
  useEffect(() => {
    traceRef.current?.scrollTo({ top: traceRef.current.scrollHeight });
  }, [lines]);

  if (!run) return null;

  const live = phase === "connecting" || phase === "running";
  const statusText =
    phase === "idle" || !targetUrl
      ? "waiting for the reported link…"
      : phase === "connecting"
        ? "connecting to the scout…"
        : phase === "running"
          ? "collecting evidence — you don't have to look"
          : phase === "done"
            ? `evidence collected · ${summary ?? ""}`
            : "scout stopped";

  return (
    <section
      className="flex flex-col overflow-hidden rounded-chip border border-[rgba(181,107,255,0.35)] bg-mira-night"
      aria-label="live agent view"
    >
      <header className="flex items-center gap-[10px] border-b border-[rgba(181,107,255,0.2)] px-[18px] py-[13px]">
        <span
          className={cn(
            "h-[9px] w-[9px] flex-shrink-0 rounded-full",
            live
              ? "animate-pulse bg-mira-electric-lilac shadow-[0_0_10px_rgba(181,107,255,0.85)]"
              : phase === "done"
                ? "bg-mira-electric-lilac"
                : "bg-mira-danger"
          )}
        />
        <span className="text-label uppercase tracking-label text-mira-muted-text">
          agent live
        </span>
        <span className="ml-auto truncate text-body-sm text-mira-muted-dim">
          {statusText}
        </span>
      </header>

      {/* Live screen — 16:10 viewport, real frames only. */}
      <div className="relative aspect-[16/10] w-full bg-mira-purple-steel">
        {frame ? (
          // eslint-disable-next-line @next/next/no-img-element -- live base64 frames, not static assets
          <img
            src={frame}
            alt="the agent's screen, live"
            className="h-full w-full object-cover object-top"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center px-6 text-center text-body-sm text-mira-muted-dim">
            {targetUrl ? "opening the reported page…" : "waiting for the reported link…"}
          </div>
        )}
        {frameLabel && (
          <span className="absolute left-[10px] top-[10px] rounded-full bg-[rgba(10,6,20,0.72)] px-[10px] py-[3px] text-[11px] text-mira-lilac-glow backdrop-blur-sm">
            {frameLabel}
          </span>
        )}
      </div>

      {/* Running trace — what the agent does and where it goes. */}
      <ol
        ref={traceRef}
        aria-live="polite"
        className="max-h-[150px] overflow-y-auto px-[18px] py-[12px] font-mono text-[11.5px] leading-[1.7]"
      >
        {lines.length === 0 ? (
          <li className="text-mira-muted-dim">standing by…</li>
        ) : (
          lines.map((l) => (
            <li key={l.id} className="flex gap-[8px]">
              <span className="flex-shrink-0 opacity-80">{l.icon}</span>
              <span className={cn("min-w-0 break-words", TONE_CLASS[l.tone])}>
                {l.text}
              </span>
            </li>
          ))
        )}
      </ol>
    </section>
  );
}
