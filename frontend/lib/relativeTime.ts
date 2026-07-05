/**
 * Formats an ISO timestamp as a short, lowercase relative time ("2h ago",
 * "5d ago"). Calm, non-urgent phrasing per the design voice — no seconds
 * countdowns, no clock. Computed against the current time so it stays correct
 * once the mock is replaced by real event-log timestamps.
 */
export function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const seconds = Math.max(0, Math.round((Date.now() - then) / 1000));

  if (seconds < 60) return "just now";

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;

  const weeks = Math.floor(days / 7);
  return `${weeks}w ago`;
}
