import { redirect } from "next/navigation";
import { getCase } from "@/lib/getCases";
import { CaseStatusView } from "@/components/case/CaseStatusView";

/**
 * Case detail. Renders the same "your case is open" view as the intake flow,
 * hydrated from the clicked case. Unknown ids redirect silently to /cases.
 */
export default async function CaseDetailPage({
  params,
}: {
  params: { caseId: string };
}) {
  const found = await getCase(params.caseId);
  if (!found) redirect("/cases");

  return (
    <CaseStatusView
      caseId={found.id}
      targetLabel={found.platformLabel}
      status={found.status}
    />
  );
}
