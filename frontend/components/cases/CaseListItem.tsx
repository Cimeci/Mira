import Link from "next/link";
import type { CaseSummary } from "@/lib/getCases";
import { formatRelativeTime } from "@/lib/relativeTime";
import { StatusLabel } from "./StatusLabel";

/**
 * One case, as a single tap target linking to its detail page. Shows exactly
 * four things — case id (mono), platform label (plain text, never a link or
 * URL), status, and last activity. No thumbnails, previews, counts, or
 * progress. Hover only shifts the border color (no added glow) to keep the
 * dashboard's glow budget on the title and the approval marker.
 */
export function CaseListItem({ item }: { item: CaseSummary }) {
  return (
    <Link
      href={`/cases/${item.id}`}
      className="block rounded-panel border border-[rgba(181,107,255,0.35)] bg-mira-purple-steel p-4 transition-colors hover:border-mira-electric-lilac sm:p-5"
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-mono text-body-sm text-mira-lilac-glow">
          {item.id}
        </span>
        <span className="font-mono text-caption text-mira-muted-text">
          updated {formatRelativeTime(item.lastActivityAt)}
        </span>
      </div>

      <p className="mt-3 font-mono text-body-lg text-mira-luminance">
        {item.platformLabel}
      </p>

      <div className="mt-2">
        <StatusLabel status={item.status} />
      </div>
    </Link>
  );
}
