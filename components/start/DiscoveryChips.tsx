"use client";

import { useFlow } from "@/lib/flow-context";
import { Chip } from "@/components/ui/Chip";

const OPTIONS = [
  "search engine",
  "social media",
  "someone sent it to me",
  "mira found it",
  "other",
];

/** Single-select discovery source chips. */
export function DiscoveryChips() {
  const { discovery, setDiscovery } = useFlow();
  return (
    <div className="flex flex-wrap gap-[10px]">
      {OPTIONS.map((label, i) => (
        <Chip
          key={label}
          label={label}
          selected={discovery === i}
          onSelect={() => setDiscovery(i)}
        />
      ))}
    </div>
  );
}
