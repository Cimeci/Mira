import type { Metadata } from "next";
import {
  LegalShell,
  LegalSection,
  LegalItem,
} from "@/components/legal/LegalShell";

export const metadata: Metadata = {
  title: "mira — terms",
  description:
    "the mandate you sign, the approvals mira waits for, and the limits of the prototype.",
};

export default function TermsScreen() {
  return (
    <LegalShell
      title="terms"
      intro="short version: you stay in charge. mira only acts inside the mandate you sign, waits for your approval before anything leaves, and this demo never touches a real platform."
      prev={{ href: "/legal/privacy", label: "privacy" }}
    >
      <LegalSection number="01" title="what mira is">
        <p>
          mira is an <strong>open-source prototype</strong> built at the raise
          hackathon 2026. it demonstrates an agent that prepares and tracks
          takedown requests for non-consensual content. it is{" "}
          <strong>not legal advice</strong> and not a substitute for a lawyer
          or for reporting to the authorities.
        </p>
      </LegalSection>

      <LegalSection number="02" title="your account">
        <p>
          the case screens are private: they require a signed-in session, and
          your case is only visible to you. you are responsible for keeping
          your credentials to yourself; sign out on shared devices.
        </p>
      </LegalSection>

      <LegalSection number="03" title="the mandate">
        <ul>
          <LegalItem>
            it authorizes mira to act in your name{" "}
            <strong>for that case only</strong>, strictly on the urls you
            provided.
          </LegalItem>
          <LegalItem>
            it lasts until the case is closed, and you can{" "}
            <strong>revoke it at any time</strong> — revocation stops
            everything.
          </LegalItem>
          <LegalItem>
            no identity document is required to sign it.
          </LegalItem>
        </ul>
      </LegalSection>

      <LegalSection number="04" title="nothing leaves without you">
        <p>
          every external step — platform report, host escalation, official
          complaint — is prepared by mira but{" "}
          <strong>waits for your explicit confirmation</strong> before it is
          sent. notices cite the exact legal basis they rely on and never
          invent penalties.
        </p>
      </LegalSection>

      <LegalSection number="05" title="acceptable use">
        <ul>
          <LegalItem>
            only report content that concerns <strong>you</strong>, or someone
            you are legally authorized to represent.
          </LegalItem>
          <LegalItem>
            knowingly filing a false report may expose you to liability under
            the laws that apply to you — do not do it.
          </LegalItem>
        </ul>
      </LegalSection>

      <LegalSection number="06" title="demo limits">
        <p>
          this demonstration runs against a <strong>mock host</strong> and a
          demo inbox only: no real platform is contacted and no real takedown
          is filed from the demo environment.
        </p>
      </LegalSection>

      <LegalSection number="07" title="no warranty">
        <p>
          the software is provided <strong>“as is”</strong>, without warranty
          of any kind, in line with its mit license. to the extent permitted
          by law, the project team is not liable for damages arising from the
          use of this prototype.
        </p>
      </LegalSection>

      <LegalSection number="08" title="changes">
        <p>
          if these terms change, the “last updated” date above changes with
          them, and the history stays public in the git repository.
        </p>
      </LegalSection>
    </LegalShell>
  );
}
