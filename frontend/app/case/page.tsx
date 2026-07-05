import { CaseCreatedView } from "@/components/case/CaseCreatedView";

/**
 * End of the case-creation flow. Opening the case here dispatches the scout for the
 * URL entered during intake (see CaseCreatedView) — the case being opened is the
 * trigger, not URL entry.
 */
export default function CaseCreatedScreen() {
  return <CaseCreatedView />;
}
