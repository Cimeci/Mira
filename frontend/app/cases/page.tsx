import { getCases } from "@/lib/getCases";
import { CasesShell } from "@/components/cases/CasesShell";
import { CaseListItem } from "@/components/cases/CaseListItem";
import { ScreenTitle } from "@/components/ui/ScreenTitle";
import { LinkButton } from "@/components/ui/LinkButton";

const FOOTER = "mira is handling it — you stay in control of every legal step.";

export default async function CasesPage() {
  const cases = await getCases();

  return (
    <CasesShell footer={FOOTER}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <ScreenTitle>your cases</ScreenTitle>
        {cases.length > 0 && (
          <LinkButton href="/start" variant="ghost" size="sm">
            start a new case
          </LinkButton>
        )}
      </div>

      {cases.length === 0 ? (
        <div className="mt-16 flex flex-col items-center gap-7 text-center">
          <p className="font-mono text-body-lg text-mira-muted-text">
            no open cases.
          </p>
          <LinkButton href="/start" variant="primary">
            start a case
          </LinkButton>
        </div>
      ) : (
        <ul className="mt-8 flex flex-col gap-4">
          {cases.map((item) => (
            <li key={item.id}>
              <CaseListItem item={item} />
            </li>
          ))}
        </ul>
      )}
    </CasesShell>
  );
}
