import type { Metadata } from "next";
import { GlowBackdrop } from "@/components/ui/GlowBackdrop";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Panel } from "@/components/ui/Panel";
import { ScreenTitle } from "@/components/ui/ScreenTitle";

export const metadata: Metadata = {
  title: "mira — legal",
  description: "legal notice, privacy, and terms for the mira prototype.",
};

function LegalSection({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Panel
      id={id}
      className="scroll-mt-24 p-6"
      aria-labelledby={`${id}-heading`}
    >
      <h2
        id={`${id}-heading`}
        className="font-display text-section uppercase tracking-display text-mira-lilac-glow"
      >
        {title}
      </h2>
      <div className="mt-4 flex flex-col gap-3 text-body-sm leading-relaxed text-mira-muted-text">
        {children}
      </div>
    </Panel>
  );
}

export default function LegalScreen() {
  return (
    <div className="relative mx-auto flex min-h-screen w-full max-w-[1440px] flex-col items-center overflow-hidden bg-mira-void">
      <GlowBackdrop />
      <Header />

      <main className="mt-10 mb-14 w-full max-w-[720px] px-5 sm:px-10 lg:px-0">
        <div className="flex flex-col gap-[26px]">
          <ScreenTitle>legal</ScreenTitle>

          <LegalSection id="mentions" title="legal notice">
            <p>
              mira is an open-source prototype built for the raise hackathon
              2026. it is a technical demonstration, not a commercial service
              and not legal advice.
            </p>
            <p>
              source code is published under the mit license at
              github.com/Cimeci/Mira. for any question about this prototype,
              open an issue on the repository.
            </p>
          </LegalSection>

          <LegalSection id="privacy" title="privacy">
            <p>
              we collect the minimum needed to open your case: an email address
              for your session, the urls you report, and your mandate
              signature. nothing else.
            </p>
            <p>
              media is never stored as raw bytes — evidence is kept as
              perceptual hashes, and anything retained is encrypted at rest.
              evidence is deleted after 90 days at the latest, and you can ask
              for erasure at any time.
            </p>
            <p>
              processing rests on your explicit consent and on the mandate you
              sign (gdpr art. 6(1)(a)); takedown notices follow the
              notice-and-action mechanism of the digital services act (dsa
              art. 16). your face-scan, when used, stays on your device — see
              the note on the signature screen.
            </p>
          </LegalSection>

          <LegalSection id="terms" title="terms">
            <p>
              by signing the mandate you authorize mira to act in your name for
              that case only. the mandate lasts until the case is closed and
              you can revoke it at any time.
            </p>
            <p>
              nothing leaves mira without you: every external step — platform
              report, host escalation, official complaint — waits for your
              explicit approval before it is sent.
            </p>
            <p>
              this demo runs against a mock host and a demo inbox only; no real
              platform is contacted.
            </p>
          </LegalSection>
        </div>
      </main>

      <Footer>mira handles the process — you stay in control of every legal step.</Footer>
    </div>
  );
}
