import type { Metadata } from "next";
import {
  LegalShell,
  LegalSection,
  LegalItem,
} from "@/components/legal/LegalShell";

export const metadata: Metadata = {
  title: "mira — privacy",
  description:
    "what mira collects, why, how long it is kept, and your gdpr rights.",
};

export default function PrivacyScreen() {
  return (
    <LegalShell
      title="privacy"
      intro="mira exists to remove non-consensual content, so it is built to hold as little of you as possible. this policy says exactly what we collect, why, for how long, and what you can demand."
      prev={{ href: "/legal/mentions", label: "legal notice" }}
      next={{ href: "/legal/terms", label: "terms" }}
    >
      <LegalSection number="01" title="what we collect">
        <ul>
          <LegalItem>
            <strong>account</strong> — the email address and password you use
            to open your session (password handled by supabase auth, never
            visible to us).
          </LegalItem>
          <LegalItem>
            <strong>your case</strong> — the urls you report, your description
            of what happened, and how you discovered the content.
          </LegalItem>
          <LegalItem>
            <strong>your mandate</strong> — the signature strokes you draw and
            the timestamp of signing.
          </LegalItem>
        </ul>
        <p>nothing else. no analytics, no advertising trackers.</p>
      </LegalSection>

      <LegalSection number="02" title="what we deliberately do not keep">
        <ul>
          <LegalItem>
            <strong>no raw media</strong> — evidence is sealed as perceptual
            hashes (a fingerprint of the image), never as the image itself.
          </LegalItem>
          <LegalItem>
            <strong>no face data leaves your device</strong> — the optional
            face-scan runs in your browser against an in-memory canvas;
            nothing is uploaded and the camera stream is stopped as soon as
            the check ends.
          </LegalItem>
          <LegalItem>
            <strong>no third-party cookies</strong> — the only storage is the
            session token that keeps you signed in.
          </LegalItem>
        </ul>
      </LegalSection>

      <LegalSection number="03" title="why we process it — legal basis">
        <p>
          we process your data on two bases under the gdpr: your{" "}
          <strong>explicit consent</strong> and the{" "}
          <strong>mandate you sign</strong> (art. 6(1)(a) and 6(1)(b) gdpr —
          consent and performance of the agreement you asked for). takedown
          notices sent on your behalf follow the notice-and-action mechanism
          of the digital services act (<strong>art. 16 dsa</strong>).
        </p>
      </LegalSection>

      <LegalSection number="04" title="how long we keep it">
        <ul>
          <LegalItem>
            <strong>evidence</strong> — encrypted at rest and deleted after{" "}
            <strong>90 days</strong> at the latest.
          </LegalItem>
          <LegalItem>
            <strong>your case record</strong> — kept while the case is open;
            you can revoke the mandate and ask for erasure at any time.
          </LegalItem>
          <LegalItem>
            <strong>your account</strong> — kept until you delete it.
          </LegalItem>
        </ul>
      </LegalSection>

      <LegalSection number="05" title="who can see it">
        <p>
          your case is visible to you alone in the interface. the database is
          locked down so the browser can read nothing directly; only the mira
          backend can access case records, and only to run the steps you
          approved. we never sell or share your data.
        </p>
      </LegalSection>

      <LegalSection number="06" title="your rights">
        <p>
          under the gdpr (art. 15–21) you can ask at any time for{" "}
          <strong>access</strong>, <strong>rectification</strong>,{" "}
          <strong>erasure</strong>, <strong>portability</strong>, or to{" "}
          <strong>withdraw your consent</strong> — withdrawing stops all
          processing without affecting what was lawfully done before. you can
          also lodge a complaint with your data protection authority (in
          france, the cnil).
        </p>
      </LegalSection>

      <LegalSection number="07" title="contact">
        <p>
          exercise any of these rights by opening an issue on the github
          repository (see the legal notice) or through the contact channel
          shown in your case view.
        </p>
      </LegalSection>
    </LegalShell>
  );
}
