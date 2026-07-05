"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useSession } from "@/lib/session-context";

/**
 * Session-only wrapper for the case flow screens. Unauthenticated visits are
 * redirected to /login carrying the intended destination, mirroring the
 * mandate gate pattern (/signature → /mandate when unsigned).
 */
export function SessionGate({ children }: { children: ReactNode }) {
  const { user, loading } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [loading, user, pathname, router]);

  // Same placeholder for "still checking" and "redirecting" — avoids flashing
  // protected content before the session state is known.
  if (loading || !user) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-mira-void">
        <div
          role="status"
          aria-live="polite"
          className="flex items-center gap-3 text-body-sm text-mira-muted-text"
        >
          <span>checking session</span>
          <span className="inline-block h-[15px] w-2 animate-blink bg-mira-electric-lilac shadow-glow-soft" />
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
