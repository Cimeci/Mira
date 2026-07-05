import { Fragment } from "react";
import { cn } from "@/lib/cn";

export type TimelineStep = { label: string; note?: string; active?: boolean };

/** The standard six-step case timeline (first step in progress, rest awaiting). */
export const DEFAULT_TIMELINE_STEPS: TimelineStep[] = [
  { label: "collect evidence", active: true },
  { label: "verify match" },
  { label: "send platform report", note: "(if chosen)" },
  { label: "escalate to host", note: "(if chosen)" },
  { label: "prepare complaint", note: "(local authority, if chosen)" },
  { label: "track takedown" },
];

/** Vertical case timeline: first step in progress, the rest awaiting. */
export function CaseTimeline({
  steps = DEFAULT_TIMELINE_STEPS,
}: {
  steps?: TimelineStep[];
}) {
  return (
    <div className="flex flex-1 flex-col rounded-chip border border-[rgba(181,107,255,0.35)] bg-mira-night p-7">
      <div className="mb-[18px] text-label uppercase tracking-label text-mira-muted-text">
        case timeline
      </div>

      {steps.map((step, i) => (
        <Fragment key={step.label}>
          <div className="flex items-center gap-[14px]">
            <div
              className={cn(
                "h-[14px] w-[14px] flex-shrink-0 rounded-full box-border",
                step.active
                  ? "animate-pulse bg-mira-electric-lilac shadow-[0_0_10px_rgba(181,107,255,0.8)]"
                  : "border border-[rgba(181,107,255,0.55)] bg-mira-purple-steel"
              )}
            />
            <div
              className={cn(
                "text-[15px]",
                step.active ? "text-mira-luminance" : "text-mira-muted-text"
              )}
            >
              {step.label}
              {step.active && (
                <span className="text-body-sm text-mira-electric-lilac">
                  {" "}
                  — in progress
                </span>
              )}
              {step.note && (
                <span className="text-body-sm text-mira-muted-dim"> {step.note}</span>
              )}
            </div>
          </div>
          {i < steps.length - 1 && (
            <div
              className={cn(
                "ml-[6.5px] h-[22px] w-px",
                i === 0
                  ? "bg-[rgba(181,107,255,0.6)]"
                  : "bg-[rgba(181,107,255,0.25)]"
              )}
            />
          )}
        </Fragment>
      ))}
    </div>
  );
}
