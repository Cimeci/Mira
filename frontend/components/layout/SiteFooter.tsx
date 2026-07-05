import Link from "next/link";
import { Logo } from "./Logo";

const REPO_URL = "https://github.com/Cimeci/Mira";

const COLUMNS: {
  heading: string;
  links: { href: string; label: string; external?: boolean }[];
}[] = [
  {
    heading: "product",
    links: [
      { href: "/start", label: "start a case" },
      { href: "/case", label: "my case" },
      { href: "/login", label: "sign in" },
    ],
  },
  {
    heading: "legal",
    links: [
      { href: "/legal", label: "overview" },
      { href: "/legal/mentions", label: "legal notice" },
      { href: "/legal/privacy", label: "privacy" },
      { href: "/legal/terms", label: "terms" },
    ],
  },
  {
    heading: "source",
    links: [
      { href: REPO_URL, label: "github repository", external: true },
      { href: `${REPO_URL}/issues`, label: "report an issue", external: true },
    ],
  },
];

/**
 * Full site footer for the standalone pages (landing, legal): brand column,
 * link columns, and a copyright bar. Rendered inside a dark brand band on the
 * landing so the neon wordmark stays legible regardless of the page theme.
 * The flow screens keep the slim trust-line `Footer` instead.
 */
export function SiteFooter() {
  return (
    <footer className="w-full border-t border-[rgba(181,107,255,0.22)] bg-[rgba(15,10,24,0.85)]">
      <div className="mx-auto grid w-full max-w-[1080px] gap-10 px-6 py-12 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr_1fr] lg:gap-6">
        <div className="flex flex-col items-start gap-4">
          <Logo />
          <p className="text-body-sm leading-[1.6] text-mira-muted-text">
            you never have to look again — mira collects evidence, notifies
            platforms, and watches for reuploads. nothing is filed without
            your approval.
          </p>
        </div>

        {COLUMNS.map((column) => (
          <nav
            key={column.heading}
            aria-label={column.heading}
            className="flex flex-col gap-3"
          >
            <h2 className="font-display text-label uppercase tracking-label text-mira-lilac-glow">
              {column.heading}
            </h2>
            <ul className="flex flex-col gap-2">
              {column.links.map((link) => (
                <li key={link.href}>
                  {link.external ? (
                    <a
                      href={link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-body-sm text-mira-muted-text underline-offset-4 transition-colors hover:text-mira-lilac-glow hover:underline"
                    >
                      {link.label} ↗
                    </a>
                  ) : (
                    <Link
                      href={link.href}
                      className="text-body-sm text-mira-muted-text underline-offset-4 transition-colors hover:text-mira-lilac-glow hover:underline"
                    >
                      {link.label}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>

      <div className="border-t border-[rgba(181,107,255,0.14)]">
        <div className="mx-auto flex w-full max-w-[1080px] flex-col items-center justify-between gap-2 px-6 py-5 text-caption text-mira-muted-dim sm:flex-row">
          <p>© 2026 mira — open source under the mit license.</p>
          <p>a raise hackathon 2026 prototype. not legal advice.</p>
        </div>
      </div>
    </footer>
  );
}
