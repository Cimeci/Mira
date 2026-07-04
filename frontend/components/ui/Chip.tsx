import { cn } from "@/lib/cn";

/** Selectable pill chip (discovery options on the start-case screen). */
export function Chip({
  label,
  selected,
  onSelect,
}: {
  label: string;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onSelect}
      className={cn(
        "rounded-full border px-[18px] py-2 text-[14px] transition-colors",
        selected
          ? "border-[rgba(181,107,255,0.55)] bg-mira-purple-steel text-mira-lilac-glow shadow-[0_0_10px_rgba(181,107,255,0.35)]"
          : "border-[rgba(181,107,255,0.35)] bg-transparent text-mira-muted-text hover:border-[rgba(181,107,255,0.5)] hover:text-mira-lilac-glow"
      )}
    >
      {label}
    </button>
  );
}
