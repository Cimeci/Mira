import Image from "next/image";
import Link from "next/link";
import { cn } from "@/lib/cn";

/** Small clickable wordmark used in the inner-screen header bar (→ home). */
export function Logo({ className }: { className?: string }) {
  return (
    <Link
      href="/"
      aria-label="mira — home"
      className={cn("inline-block", className)}
    >
      <Image
        src="/assets/logo_txt.png"
        alt="mira"
        width={110}
        height={40}
        priority
        className="block h-auto w-[110px] [filter:drop-shadow(0_0_10px_rgba(181,107,255,0.5))]"
      />
    </Link>
  );
}
