"use client";

import { useEffect, useState } from "react";
import { getCases, type CaseSummary } from "@/lib/getCases";
import { CasesShell } from "@/components/cases/CasesShell";
import { CaseListItem } from "@/components/cases/CaseListItem";
import { ScreenTitle } from "@/components/ui/ScreenTitle";
import { LinkButton } from "@/components/ui/LinkButton";

const FOOTER = "mira is handling it — you stay in control of every legal step.";
// Light poll so a case that advances (or a fresh one) shows up without a reload.
const POLL_MS = 2500;

export default function CasesPage() {
  const [cases, setCases] = useState<CaseSummary[] | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      const next = await getCases();
      if (active) setCases(next);
    };
    load();
    const timer = setInterval(load, POLL_MS);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const list = cases ?? [];

  return (
    <CasesShell footer={FOOTER}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <ScreenTitle>your cases</ScreenTitle>
        {list.length > 0 && (
          <LinkButton href="/start" variant="ghost" size="sm">
            start a new case
          </LinkButton>
        )}
      </div>

      {cases === null ? (
        <p className="mt-16 text-center font-mono text-body-lg text-mira-muted-text">
          loading…
        </p>
      ) : list.length === 0 ? (
        <div className="mt-16 flex flex-col items-center gap-7 text-center">
          <p className="font-mono text-body-lg text-mira-muted-text">
            no open cases.
          </p>
          <LinkButton href="/start" variant="primary">
            start a case
          </LinkButton>
        </div>
      ) : (
        <ul className="mt-8 flex flex-col gap-4">
          {list.map((item) => (
            <li key={item.id}>
              <CaseListItem item={item} />
            </li>
          ))}
        </ul>
      )}
    </CasesShell>
  );
}
