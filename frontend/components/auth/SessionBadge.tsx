"use client";

import { useSession } from "@/lib/session-context";
import { Button } from "@/components/ui/Button";

/** Header-right session indicator: signed-in email + sign out. */
export function SessionBadge() {
  const { user, loading, signOut } = useSession();

  if (loading || !user) return null;

  return (
    <div className="flex items-center gap-3">
      <span className="hidden text-caption text-mira-muted-text sm:inline">
        {user.email}
      </span>
      <Button
        variant="ghost"
        size="sm"
        onClick={() =>
          void signOut().then((error) => {
            if (error) console.error("sign out failed:", error);
          })
        }
      >
        sign out
      </Button>
    </div>
  );
}
