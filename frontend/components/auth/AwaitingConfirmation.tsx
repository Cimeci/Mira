"use client";

import { useCallback, useEffect, useState } from "react";
import { useSession } from "@/lib/session-context";
import { Panel } from "@/components/ui/Panel";
import { ScreenTitle } from "@/components/ui/ScreenTitle";
import { Button } from "@/components/ui/Button";

const POLL_MS = 4000;

/**
 * Post-sign-up holding screen while the account's email is unconfirmed. It
 * quietly retries sign-in on a timer: the moment the user clicks the link in
 * their inbox, sign-in starts succeeding, session-context's onAuthStateChange
 * flips `user`, and LoginForm's redirect effect carries them to their case.
 */
export function AwaitingConfirmation({
  email,
  password,
  onBack,
}: {
  email: string;
  password: string;
  onBack: () => void;
}) {
  const { signIn } = useSession();
  const [checking, setChecking] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  const attempt = useCallback(async () => {
    const err = await signIn(email, password);
    // null → signed in; the redirect is handled once `user` updates.
    // "email not confirmed" is the expected waiting state, so stay quiet.
    if (err && !/not confirmed/i.test(err)) setNote(err);
    return err;
  }, [signIn, email, password]);

  useEffect(() => {
    let active = true;
    const id = setInterval(() => {
      if (active) void attempt();
    }, POLL_MS);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [attempt]);

  const checkNow = async () => {
    setChecking(true);
    setNote(null);
    const err = await attempt();
    setChecking(false);
    if (err && /not confirmed/i.test(err)) {
      setNote("not confirmed yet — open the link in your inbox, then retry.");
    }
  };

  return (
    <div className="flex flex-col gap-[26px]">
      <ScreenTitle>confirm your email</ScreenTitle>

      <Panel className="flex flex-col items-center gap-5 p-8 text-center">
        <div className="flex items-center gap-2" role="status" aria-live="polite">
          <span className="inline-block h-[15px] w-2 animate-blink bg-mira-electric-lilac shadow-glow-soft" />
          <span className="text-caption uppercase tracking-label text-mira-muted-dim">
            waiting for confirmation
          </span>
        </div>

        <p className="text-body-sm leading-[1.6] text-mira-muted-text">
          we sent a confirmation link to{" "}
          <span className="text-mira-lilac-glow">{email}</span>. open it to
          activate your account — this page continues on its own.
        </p>

        {note && (
          <p role="alert" className="text-caption text-mira-danger">
            {note}
          </p>
        )}

        <div className="flex flex-wrap items-center justify-center gap-3">
          <Button
            variant="flow"
            size="md"
            onClick={() => void checkNow()}
            disabled={checking}
          >
            {checking ? "checking…" : "i've confirmed — continue"}
          </Button>
          <Button variant="ghost" size="md" onClick={onBack}>
            use another email
          </Button>
        </div>
      </Panel>
    </div>
  );
}
