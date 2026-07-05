"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useFlow } from "@/lib/flow-context";
import { ScreenTitle } from "@/components/ui/ScreenTitle";
import { LinkButton } from "@/components/ui/LinkButton";
import { BackButton } from "@/components/ui/BackButton";
import { Button } from "@/components/ui/Button";
import { CaseCard } from "./CaseCard";
import { verifyFace, fetchImageAsDataUrl } from "@/lib/faceVerifier";

type CreateState = "verifying" | "creating" | "ready" | "error" | "nomatch";

/** Placeholder shown only when the user opened a case without typing any url. */
const DEMO_TARGET_LABEL = "mock-host.local/media/xyz789";

/**
 * Normalizes a user-typed url into an absolute http(s) url the backend will
 * accept as scope, or null if it can't be one. A bare host ("site.com/x") is
 * assumed https so pasting without a scheme still works. Kept lenient on the
 * client; the backend (mandate._validate_scope) is the real gate.
 */
function normalizeUrl(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const candidate = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
  try {
    const url = new URL(candidate);
    return url.hostname ? url.toString() : null;
  } catch {
    return null;
  }
}

/** Compact host+path label for the case card (drops scheme and trailing slash). */
function targetLabel(url: string): string {
  try {
    const u = new URL(url);
    return (u.host + u.pathname).replace(/\/$/, "") || u.host;
  } catch {
    return url;
  }
}

/**
 * Turns the narrative "your case is open" screen into a real case: it POSTs to
 * the backend once (guarded against StrictMode double-invoke and back-nav via
 * the flow context), so a real case exists server-side before the user reaches
 * the /cases dashboard.
 */
export function CaseOpenPanel({ apiBase }: { apiBase: string }) {
  const { caseId, setCaseId, urls, faceEmbedding } = useFlow();
  const [state, setState] = useState<CreateState>(caseId ? "ready" : "creating");
  const [errorDetail, setErrorDetail] = useState("");
  const [similarity, setSimilarity] = useState<number | null>(null);
  const started = useRef(false);

  // The real urls the user typed on /start become the case scope. Empty -> the
  // backend falls back to the pre-authorized demo mandate (mock host).
  const scopeUrls = useMemo(
    () => urls.map(normalizeUrl).filter((u): u is string => u !== null),
    [urls]
  );
  const displayUrl = scopeUrls[0] ? targetLabel(scopeUrls[0]) : DEMO_TARGET_LABEL;

  useEffect(() => {
    if (caseId) {
      setState("ready");
      return;
    }
    if (started.current) return;
    started.current = true;

    (async () => {
      // Face-match pre-check: only open a case if the suspected content actually
      // contains the victim's scanned face. Skipped when there's no enrolled
      // embedding (no-camera demo) or the content image can't be fetched (CORS /
      // not a direct image) — we never fake a match, and never block silently.
      const target = scopeUrls[0];
      if (faceEmbedding && target) {
        setState("verifying");
        const image = await fetchImageAsDataUrl(target);
        if (image) {
          const v = await verifyFace({
            caseId: "match-precheck",
            sourceUrl: target,
            imageDataUrl: image,
            referenceEmbedding: faceEmbedding,
          });
          if (v.ok && !v.isMatch) {
            setSimilarity(v.similarityScore);
            setState("nomatch");
            return;
          }
        }
      }

      setState("creating");
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 5000);
      try {
        const res = await fetch(`${apiBase}/cases`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: scopeUrls.length
            ? JSON.stringify({ scope_urls: scopeUrls })
            : "{}",
          signal: controller.signal,
        });
        if (!res.ok) {
          // Surface the backend's reason (e.g. off-allow-list host) instead of a
          // generic failure — a silent 400 during the demo is undebuggable.
          let detail = `status ${res.status}`;
          try {
            const body = (await res.json()) as { detail?: string };
            if (body?.detail) detail = body.detail;
          } catch {
            /* non-JSON error body — keep the status line */
          }
          setErrorDetail(detail);
          throw new Error(detail);
        }
        const data = (await res.json()) as { case_id: string };
        setCaseId(data.case_id);
        setState("ready");
      } catch {
        setState("error");
      } finally {
        clearTimeout(timer);
      }
    })();
  }, [apiBase, caseId, setCaseId, scopeUrls, faceEmbedding]);

  if (state === "nomatch") {
    const pct = similarity != null ? `${Math.round(similarity * 100)}%` : null;
    return (
      <div className="flex w-full flex-col gap-[22px] md:w-[400px] md:flex-shrink-0">
        <ScreenTitle>no facial match</ScreenTitle>

        <CaseCard caseId="—" targetLabel={displayUrl} status="no facial match" />

        <p className="text-[14px] leading-[1.5] text-mira-muted-text">
          this content doesn&rsquo;t appear to contain your face
          {pct ? ` (similarity ${pct})` : ""}. mira only opens a case for content
          that matches you — nothing was opened.
        </p>

        <div className="flex flex-wrap items-center gap-[14px]">
          <BackButton href="/signature" />
          <LinkButton href="/start" variant="ghost" size="md">
            try another link
          </LinkButton>
        </div>
      </div>
    );
  }

  const cardId =
    state === "ready" ? caseId : state === "error" ? "—" : "opening…";
  const cardStatus =
    state === "ready"
      ? "evidence collection started"
      : state === "error"
        ? "mira api unreachable"
        : state === "verifying"
          ? "checking for a facial match…"
          : "opening your case…";

  return (
    <div className="flex w-full flex-col gap-[22px] md:w-[400px] md:flex-shrink-0">
      <ScreenTitle>your case is open ✓</ScreenTitle>

      <CaseCard caseId={cardId} targetLabel={displayUrl} status={cardStatus} />

      <p className="text-[14px] leading-[1.5] text-mira-muted-text">
        our scout is now collecting and verifying evidence. we&rsquo;ll notify
        you before any step that needs your approval.
      </p>

      <div className="flex flex-wrap items-center gap-[14px]">
        <BackButton href="/signature" />
        {state === "ready" ? (
          <LinkButton href="/cases" variant="flow" className="px-7">
            go to case dashboard
          </LinkButton>
        ) : (
          <Button variant="flow" size="lg" className="px-7" disabled>
            {state === "error" ? "unavailable" : "opening…"}
          </Button>
        )}
      </div>

      {state === "error" && (
        <p className="text-caption text-mira-danger">
          {errorDetail
            ? `couldn't open this case — ${errorDetail}`
            : "couldn't open a live case — is the backend running?"}{" "}
          {!errorDetail && (
            <>
              start it with <span className="font-mono">bash dev.sh</span>, then
              reload.
            </>
          )}
        </p>
      )}
    </div>
  );
}
