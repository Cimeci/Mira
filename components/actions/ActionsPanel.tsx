"use client";

import { useFlow } from "@/lib/flow-context";

const ACTIONS = [
  {
    title: "report to the platform",
    desc: "we prepare and send a takedown request to the website or app.",
  },
  {
    title: "contact the host / server provider",
    desc: "if the platform does not respond, we escalate to the infrastructure provider.",
  },
  {
    title: "file an official complaint",
    desc: "for france: complaint via gendarmerie / cybercrime reporting. needs your approval and signature.",
  },
];

/** The recommended "do everything" card plus three toggleable action paths. */
export function ActionsPanel() {
  const { actions, setActions } = useFlow();

  const toggle = (i: number) => {
    const next = actions.slice() as [boolean, boolean, boolean];
    next[i] = !next[i];
    setActions(next);
  };

  const pickAll = () => setActions([true, true, true]);

  return (
    <div className="flex flex-col gap-[18px]">
      <button
        type="button"
        onClick={pickAll}
        className="relative cursor-pointer rounded-chip border border-mira-electric-lilac bg-mira-purple-steel px-5 py-[18px] text-left shadow-[0_0_0_1px_rgba(181,107,255,0.5),0_0_18px_rgba(181,107,255,0.3)]"
      >
        <span className="absolute -top-[11px] right-4 rounded-[3px] bg-mira-electric-lilac px-3 py-[3px] font-display text-[10px] uppercase tracking-label text-mira-void shadow-[0_0_12px_rgba(181,107,255,0.6)]">
          recommended ✓
        </span>
        <span className="block text-[17px] text-mira-luminance">
          do everything possible
        </span>
        <span className="mt-1 block text-body-sm text-mira-muted-text">
          all three paths below, in order — mira escalates for you.
        </span>
      </button>

      {ACTIONS.map((a, i) => (
        <button
          key={a.title}
          type="button"
          role="checkbox"
          aria-checked={actions[i]}
          onClick={() => toggle(i)}
          className="flex cursor-pointer items-start gap-4 rounded-chip border border-[rgba(181,107,255,0.35)] bg-mira-night px-5 py-[18px] text-left transition-colors hover:border-[rgba(181,107,255,0.6)]"
        >
          <span className="mt-[3px] flex h-[18px] w-[18px] flex-shrink-0 items-center justify-center rounded-[3px] border border-mira-electric-lilac bg-mira-purple-steel text-body-sm text-mira-lilac-glow">
            {actions[i] ? "✓" : ""}
          </span>
          <span>
            <span className="block text-[16px] text-mira-luminance">
              {a.title}
            </span>
            <span className="mt-1 block text-body-sm text-mira-muted-text">
              {a.desc}
            </span>
          </span>
        </button>
      ))}
    </div>
  );
}
