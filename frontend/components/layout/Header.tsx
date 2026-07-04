import { Logo } from "./Logo";

/** Inner-screen top bar: clickable wordmark that returns home. */
export function Header() {
  return (
    <header className="relative flex w-full items-center justify-between border-b border-[rgba(181,107,255,0.22)] px-10 py-[22px]">
      <Logo />
    </header>
  );
}
