"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { User } from "@supabase/supabase-js";
import { getSupabase } from "./supabase";

export interface SignUpResult {
  error: string | null;
  /** true when the project requires email confirmation before a session opens */
  needsConfirmation: boolean;
}

interface SessionContextValue {
  user: User | null;
  /** true until the initial getSession() resolves — gates render nothing yet */
  loading: boolean;
  /** non-null when the Supabase env vars are missing (shown on /login) */
  configError: string | null;
  signIn: (email: string, password: string) => Promise<string | null>;
  signUp: (email: string, password: string) => Promise<SignUpResult>;
  /** resolves to an error message, or null on success */
  signOut: () => Promise<string | null>;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [configError, setConfigError] = useState<string | null>(null);

  useEffect(() => {
    let supabase;
    try {
      supabase = getSupabase();
    } catch (error: unknown) {
      // Surface the misconfiguration on /login instead of blanking every route.
      const message =
        error instanceof Error ? error.message : "supabase init failed";
      console.error(message);
      setConfigError(message);
      setLoading(false);
      return;
    }

    supabase.auth
      .getSession()
      .then(({ data }) => setUser(data.session?.user ?? null))
      .finally(() => setLoading(false));

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const { error } = await getSupabase().auth.signInWithPassword({
      email,
      password,
    });
    return error ? error.message : null;
  }, []);

  const signUp = useCallback(
    async (email: string, password: string): Promise<SignUpResult> => {
      const { data, error } = await getSupabase().auth.signUp({
        email,
        password,
      });
      if (error) return { error: error.message, needsConfirmation: false };
      return { error: null, needsConfirmation: !data.session };
    },
    []
  );

  const signOut = useCallback(async () => {
    const { error } = await getSupabase().auth.signOut();
    return error ? error.message : null;
  }, []);

  const value = useMemo<SessionContextValue>(
    () => ({ user, loading, configError, signIn, signUp, signOut }),
    [user, loading, configError, signIn, signUp, signOut]
  );

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within a SessionProvider");
  return ctx;
}
