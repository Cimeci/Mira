import { Logo } from "./Logo";
import { SessionBadge } from "@/components/auth/SessionBadge";

/** Inner-screen top bar: clickable wordmark home link + session indicator. */
export function Header() {
  return (
    <header className="relative flex w-full items-center justify-between border-b border-[rgba(181,107,255,0.22)] px-10 py-[22px]">
      <Logo />
      <SessionBadge />
    </header>
  );
}
