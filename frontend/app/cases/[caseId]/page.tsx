import { CaseDetailLive } from "@/components/case/CaseDetailLive";

/**
 * Case detail route. Thin server wrapper: the live view (snapshot + SSE stream
 * + G-7 approval gate) is a client component driven by the backend pipeline.
 */
export default function CaseDetailPage({ params }: { params: { caseId: string } }) {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "";
  return <CaseDetailLive caseId={params.caseId} apiBase={apiBase} />;
}
