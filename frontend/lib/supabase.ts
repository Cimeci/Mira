import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | null = null;

/**
 * Browser Supabase client, created lazily so a missing config fails loudly at
 * the auth boundary (login / session check) instead of crashing every route
 * at import time. The anon key is safe to expose: table access is gated by
 * RLS, and this client is only used for auth.
 */
export function getSupabase(): SupabaseClient {
  if (client) return client;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) {
    throw new Error(
      "supabase config missing — copy frontend/.env.example to frontend/.env.local and fill NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY"
    );
  }

  client = createClient(url, anonKey);
  return client;
}
