import type { Metadata } from "next";
import { Silkscreen, IBM_Plex_Mono } from "next/font/google";
import { FlowProvider } from "@/lib/flow-context";
import { SessionProvider } from "@/lib/session-context";
import "./globals.css";

const silkscreen = Silkscreen({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-silkscreen",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  weight: ["400", "500"],
  subsets: ["latin"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "mira — you never have to look again",
  description:
    "mira collects evidence, contacts platforms, files reports, takes down abuse, and watches for reuploads — you stay in control of every legal step.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${silkscreen.variable} ${plexMono.variable}`}>
      <body className="min-h-screen bg-mira-void-deep font-mono text-mira-luminance antialiased">
        <SessionProvider>
          <FlowProvider>{children}</FlowProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
