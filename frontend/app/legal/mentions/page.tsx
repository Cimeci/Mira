import type { Metadata } from "next";
import {
  LegalShell,
  LegalSection,
  LegalItem,
} from "@/components/legal/LegalShell";

export const metadata: Metadata = {
  title: "mira — legal notice",
  description: "publisher, hosting, license, and contact for the mira prototype.",
};

export default function LegalNoticeScreen() {
  return (
    <LegalShell
      title="legal notice"
      intro="who publishes mira, where it runs, and under which license — the identification details a site is expected to disclose."
      next={{ href: "/legal/privacy", label: "privacy" }}
    >
      <LegalSection number="01" title="publisher">
        <p>
          mira is published by the <strong>mira project team</strong>, a
          five-person team formed for the raise hackathon 2026. it is a
          technical prototype — <strong>not a commercial service</strong> and
          not legal advice. no legal entity has been incorporated for this
          project.
        </p>
      </LegalSection>

      <LegalSection number="02" title="hosting">
        <p>the prototype runs on the following infrastructure:</p>
        <ul>
          <LegalItem>
            <strong>frontend</strong> — vercel inc., 340 s lemon ave #4133,
            walnut, ca 91789, usa.
          </LegalItem>
          <LegalItem>
            <strong>authentication &amp; database</strong> — supabase inc.,
            970 toa payoh north #07-04, singapore 318992 (project hosted in
            the eu region).
          </LegalItem>
        </ul>
      </LegalSection>

      <LegalSection number="03" title="intellectual property">
        <p>
          the source code is open source, published under the{" "}
          <strong>mit license</strong> at{" "}
          <a
            href="https://github.com/Cimeci/Mira"
            target="_blank"
            rel="noopener noreferrer"
            className="text-mira-lilac-glow underline underline-offset-4 hover:text-mira-luminance"
          >
            github.com/Cimeci/Mira ↗
          </a>
          . you may reuse it under the terms of that license. the mira name,
          wordmark, and pixel-eye artwork belong to the project team.
        </p>
      </LegalSection>

      <LegalSection number="04" title="contact">
        <p>
          for any question about this prototype — including legal, privacy, or
          security matters — open an issue on the github repository. there is
          no phone or postal support for a hackathon prototype.
        </p>
      </LegalSection>
    </LegalShell>
  );
}
