/** Case summary card: id, target url, and the pulsing live status chip. */
export function CaseCard() {
  return (
    <div className="flex flex-col gap-3 rounded-chip border border-[rgba(181,107,255,0.35)] bg-mira-night px-5 py-[18px] text-[14px]">
      <div className="flex justify-between gap-3">
        <span className="text-mira-muted-text">case id</span>
        <span className="font-display text-mira-lilac-glow">mira-4821</span>
      </div>
      <div className="flex justify-between gap-3">
        <span className="text-mira-muted-text">target url</span>
        <span className="text-mira-muted-dim">[url]</span>
      </div>
      <div className="flex items-center justify-between gap-3">
        <span className="text-mira-muted-text">status</span>
        <span className="animate-pulse rounded-full border border-[rgba(181,107,255,0.55)] bg-mira-purple-steel px-3 py-[3px] text-caption text-mira-lilac-glow">
          evidence collection started
        </span>
      </div>
    </div>
  );
}
