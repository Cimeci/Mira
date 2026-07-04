import { cn } from "@/lib/cn";

/**
 * Step progress: a label beside five segments, `filled` of which glow.
 * Spans the full width of its container (which matches each screen's content
 * column), so bar and content edges align.
 */
export function ProgressBar({
  label,
  filled,
  total = 5,
}: {
  label: string;
  filled: number;
  total?: number;
}) {
  return (
    <div className="relative flex w-full items-center gap-[6px]">
      <div className="mr-2 whitespace-nowrap text-caption uppercase tracking-label text-mira-muted-text">
        {label}
      </div>
      {Array.from({ length: total }, (_, i) => {
        const on = i < filled;
        return (
          <div
            key={i}
            className={cn(
              "h-[5px] flex-1 rounded-full box-border",
              on
                ? "bg-mira-electric-lilac shadow-[0_0_8px_rgba(181,107,255,0.7)]"
                : "border border-[rgba(181,107,255,0.3)] bg-[rgba(181,107,255,0.2)]"
            )}
          />
        );
      })}
    </div>
  );
}
