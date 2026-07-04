"use client";

import { useFlow } from "@/lib/flow-context";
import { Input } from "@/components/ui/Input";

/** Line-by-line URL entry: add rows, remove rows (last row clears instead). */
export function UrlList() {
  const { urls, setUrls } = useFlow();

  const change = (i: number, value: string) => {
    const next = urls.slice();
    next[i] = value;
    setUrls(next);
  };

  const remove = (i: number) => {
    const next = urls.slice();
    if (next.length > 1) next.splice(i, 1);
    else next[0] = "";
    setUrls(next);
  };

  const add = () => setUrls([...urls, ""]);

  return (
    <div className="flex flex-col gap-[10px]">
      {urls.map((val, i) => (
        <div key={i} className="flex items-center gap-[10px]">
          <Input
            value={val}
            onChange={(e) => change(i, e.target.value)}
            placeholder="paste a url…"
            aria-label={`target url ${i + 1}`}
            className="flex-1"
          />
          <button
            type="button"
            onClick={() => remove(i)}
            aria-label={`remove url ${i + 1}`}
            className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-chip border border-[rgba(181,107,255,0.35)] text-[18px] text-mira-muted-dim transition-colors hover:border-[rgba(181,107,255,0.55)] hover:text-mira-lilac-glow"
          >
            ×
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={add}
        className="flex items-center gap-2 self-start rounded-chip border border-dashed border-[rgba(181,107,255,0.45)] px-[14px] py-2 text-body-sm uppercase tracking-[0.06em] text-mira-muted-text transition-colors hover:border-mira-electric-lilac hover:text-mira-lilac-glow"
      >
        <span className="text-mira-electric-lilac">+</span> add another url
      </button>
    </div>
  );
}
