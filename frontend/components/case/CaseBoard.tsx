"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import { ScreenTitle } from "@/components/ui/ScreenTitle";
import { LinkButton } from "@/components/ui/LinkButton";
import { CaseCard } from "./CaseCard";

/** Shape returned by GET /cases (mira/api.py:list_cases). */
interface ApiCase {
  case_id: string;
  finished: boolean;
  current_status: string | null;
  statuses: Record<string, string>;
  created_at: string | null;
}

type LoadState = "loading" | "ready" | "error";

/** The first in-scope media url doubles as the card's target line. */
function targetLabel(c: ApiCase): string {
  return Object.keys(c.statuses ?? {})[0] ?? "collecting evidence…";
}

export function CaseBoard({ apiBase }: { apiBase: string }) {
  const [cases, setCases] = useState<ApiCase[]>([]);
  const [state, setState] = useState<LoadState>("loading");

  const load = useCallback(async () => {
    setState("loading");
    // Hard timeout so a down/misconfigured backend surfaces an error screen
    // instead of leaving the skeletons spinning forever.
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    try {
      const res = await fetch(`${apiBase}/cases`, {
        cache: "no-store",
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data = (await res.json()) as { cases: ApiCase[] };
      setCases(data.cases ?? []);
      setState("ready");
    } catch {
      setState("error");
    } finally {
      clearTimeout(timer);
    }
  }, [apiBase]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-2">
            <ScreenTitle>your cases</ScreenTitle>
            <p className="max-w-[520px] text-body-sm leading-[1.55] text-mira-muted-text">
              every case mira is working — collect, verify, notify. you approve
              anything that leaves the building.
            </p>
          </div>
          <LinkButton href="/start" variant="flow" size="md">
            + start a new case
          </LinkButton>
        </div>

        {state === "ready" && cases.length > 0 && <StatsRow cases={cases} />}
      </header>

      {state === "loading" && <CaseSkeletonGrid />}

      {state === "error" && (
        <div className="flex flex-col items-center gap-4 rounded-card border border-mira-danger bg-mira-night p-12 text-center">
          <p className="text-body-lg text-mira-lilac-glow">backend unreachable</p>
          <p className="text-body-sm text-mira-muted-dim max-w-[440px]">
            the mira api isn&rsquo;t responding. start it with{" "}
            <code className="font-mono text-mira-muted-text">bash dev.sh</code>{" "}
            (or check NEXT_PUBLIC_API_BASE), then retry.
          </p>
          <button
            onClick={load}
            className="mira-clip flex min-h-[40px] items-center border border-mira-electric-lilac bg-mira-night px-6 font-display text-label uppercase tracking-label text-mira-lilac-glow transition-colors hover:bg-mira-purple-steel hover:text-mira-luminance"
          >
            retry
          </button>
        </div>
      )}

      {state === "ready" && cases.length === 0 && (
        <div className="flex flex-col items-center gap-4 rounded-card border border-[rgba(181,107,255,0.35)] bg-mira-night p-12 text-center">
          <p className="text-body-lg text-mira-muted-text">no cases yet</p>
          <p className="text-body-sm text-mira-muted-dim max-w-[420px]">
            start a case and watch mira&rsquo;s three agents collect, verify, and
            notify — live, step by step.
          </p>
          <LinkButton href="/start" variant="flow" className="mt-2">
            start your first case
          </LinkButton>
        </div>
      )}

      {state === "ready" && cases.length > 0 && (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {cases.map((c) => (
            <Link
              key={c.case_id}
              href={`/case/${c.case_id}/live`}
              className="group block h-full rounded-card transition-transform duration-200 hover:-translate-y-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-mira-electric-lilac"
            >
              <CaseCard
                caseId={c.case_id}
                targetUrl={targetLabel(c)}
                status={c.current_status}
                createdAt={c.created_at}
              />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

/** Compact at-a-glance counters above the case grid. */
function StatsRow({ cases }: { cases: ApiCase[] }) {
  const live = cases.filter((c) => !c.finished).length;
  const needsYou = cases.filter((c) => c.current_status === "AWAITING_CONFIRM").length;
  const done = cases.filter(
    (c) => c.current_status === "NOTIFIED" || c.current_status === "CONFIRMED"
  ).length;

  const tiles = [
    { value: cases.length, label: "total", accent: false },
    { value: live, label: "live now", accent: false },
    { value: needsYou, label: "need you", accent: needsYou > 0 },
    { value: done, label: "resolved", accent: false },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {tiles.map((t) => (
        <div
          key={t.label}
          className={cn(
            "flex flex-col gap-1 rounded-card border bg-mira-night px-4 py-3 transition-colors",
            t.accent
              ? "border-[rgba(255,198,92,0.5)] bg-[rgba(255,198,92,0.07)]"
              : "border-[rgba(181,107,255,0.25)]"
          )}
        >
          <span
            className={cn(
              "font-display text-[26px] leading-none",
              t.accent ? "text-mira-warn" : "text-mira-lilac-glow"
            )}
          >
            {t.value}
          </span>
          <span className="text-caption uppercase tracking-label text-mira-muted-dim">
            {t.label}
          </span>
        </div>
      ))}
    </div>
  );
}

function CaseSkeletonGrid() {
  return (
    <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className={cn(
            "h-[132px] animate-pulse rounded-chip border border-[rgba(181,107,255,0.2)] bg-mira-night",
            "shadow-[0_0_12px_rgba(181,107,255,0.08)]"
          )}
        />
      ))}
    </div>
  );
}
