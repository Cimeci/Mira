import { cn } from "@/lib/cn";
import type { CaseStatus } from "@/lib/getCases";

/**
 * Text color per status, drawn only from design tokens. Red is never used —
 * escalation reads as electric lilac like every other active state, and the
 * "awaiting your approval" accent is the same electric lilac plus a marker (see
 * below), not an alarm color.
 */
const colorByStatus: Record<CaseStatus, string> = {
  "collecting evidence": "text-mira-electric-lilac",
  "verifying match": "text-mira-electric-lilac",
  "awaiting your approval": "text-mira-electric-lilac",
  "report sent": "text-mira-lilac-glow",
  "escalated to host": "text-mira-electric-lilac",
  "takedown confirmed": "text-mira-luminance",
};

/**
 * Renders a case status as plain, lowercase text. When the case is awaiting the
 * user's approval it gets a small glowing accent dot — one of the two rationed
 * glows on the dashboard (the page title is the other). The pulse animation is
 * disabled under prefers-reduced-motion by the global rule in globals.css.
 */
export function StatusLabel({ status }: { status: CaseStatus }) {
  const needsApproval = status === "awaiting your approval";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 font-mono text-body-sm",
        colorByStatus[status]
      )}
    >
      {needsApproval && (
        <span
          aria-hidden
          className="h-[7px] w-[7px] flex-shrink-0 animate-softpulse rounded-full bg-mira-electric-lilac shadow-glow-soft"
        />
      )}
      {status}
    </span>
  );
}
