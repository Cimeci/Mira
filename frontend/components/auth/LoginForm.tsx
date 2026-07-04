"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useSession } from "@/lib/session-context";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Panel } from "@/components/ui/Panel";
import { FieldLabel } from "@/components/ui/FieldLabel";
import { ScreenTitle } from "@/components/ui/ScreenTitle";

type Mode = "sign-in" | "sign-up";

/**
 * Only /-rooted paths — a next like https://evil.example must not win.
 * Backslashes are rejected too: browsers normalize /\evil.com to //evil.com.
 */
function safeNext(raw: string | null): string {
  return raw && raw.startsWith("/") && !raw.startsWith("//") && !raw.includes("\\")
    ? raw
    : "/start";
}

export function LoginForm() {
  const { user, loading, configError, signIn, signUp } = useSession();
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));

  const [mode, setMode] = useState<Mode>("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  // Already signed in (or just signed in): continue to the intended screen.
  useEffect(() => {
    if (!loading && user) router.replace(next);
  }, [loading, user, next, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setInfo(null);
    setSubmitting(true);
    try {
      if (mode === "sign-in") {
        setError(await signIn(email, password));
      } else {
        const result = await signUp(email, password);
        setError(result.error);
        if (!result.error && result.needsConfirmation) {
          setInfo("account created — confirm it from your inbox, then sign in.");
          setMode("sign-in");
        }
      }
    } catch (submitError: unknown) {
      setError(
        submitError instanceof Error ? submitError.message : "sign-in failed"
      );
    } finally {
      setSubmitting(false);
    }
  }

  const otherMode: Mode = mode === "sign-in" ? "sign-up" : "sign-in";

  return (
    <div className="flex flex-col gap-[26px]">
      <ScreenTitle>
        {mode === "sign-in" ? "sign in" : "create your account"}
      </ScreenTitle>

      <p className="text-body-sm text-mira-muted-text">
        your case lives in a private session — sign in so only you can see it.
      </p>

      <Panel className="flex flex-col gap-5 p-6">
        <form
          className="flex flex-col gap-5"
          onSubmit={(event) => void handleSubmit(event)}
        >
          <div className="flex flex-col gap-2">
            <FieldLabel htmlFor="login-email">email</FieldLabel>
            <Input
              id="login-email"
              type="email"
              autoComplete="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <FieldLabel htmlFor="login-password">password</FieldLabel>
            <Input
              id="login-password"
              type="password"
              autoComplete={
                mode === "sign-in" ? "current-password" : "new-password"
              }
              required
              minLength={6}
              placeholder="••••••••"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          {configError && (
            <p role="alert" className="text-body-sm text-mira-danger">
              {configError}
            </p>
          )}
          {error && (
            <p role="alert" className="text-body-sm text-mira-danger">
              {error}
            </p>
          )}
          {info && (
            <p role="status" className="text-body-sm text-mira-lilac-glow">
              {info}
            </p>
          )}

          <Button
            type="submit"
            variant="flow"
            disabled={submitting || Boolean(configError)}
            className="disabled:opacity-60"
          >
            {submitting
              ? "…"
              : mode === "sign-in"
                ? "sign in"
                : "create account"}
          </Button>
        </form>

        <button
          type="button"
          onClick={() => {
            setMode(otherMode);
            setError(null);
            setInfo(null);
          }}
          className="cursor-pointer text-caption text-mira-muted-text underline-offset-4 hover:text-mira-lilac-glow hover:underline"
        >
          {mode === "sign-in"
            ? "no account yet? create one"
            : "already have an account? sign in"}
        </button>
      </Panel>
    </div>
  );
}
