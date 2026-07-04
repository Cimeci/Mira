"""Phase 0 — smoke test d'accès à Gemini Computer Use.

Vérifie 3 choses, dans l'ordre, et s'arrête à la première qui casse (fail fast) :
  1. la clé `GOOGLE_GENERATIVE_AI_API_KEY` est présente dans `.env.local` ;
  2. la clé est valide (un appel minimal passe) ;
  3. un modèle computer-use est visible pour cette clé (preview → l'accès peut varier).

Usage : .venv/bin/python scripts/cu_smoke.py
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from google import genai

# Modèle pressenti (preview) — l'étape 3 liste ce que la clé voit réellement.
CU_MODEL_HINT = "gemini-2.5-computer-use-preview-10-2025"


def main() -> None:
    load_dotenv(".env.local")
    api_key = os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY")
    if not api_key:
        sys.exit(
            "❌ GOOGLE_GENERATIVE_AI_API_KEY absente.\n"
            "   → https://aistudio.google.com → Get API key → coller dans .env.local"
        )
    print("1/3 ✅ clé présente")

    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(model="gemini-2.5-flash", contents="ping")
    assert resp.text, "réponse vide — clé ou quota en cause"
    print(f"2/3 ✅ appel API OK ({resp.text.strip()[:30]!r})")

    cu_models = [m.name for m in client.models.list() if "computer-use" in m.name]
    if not cu_models:
        sys.exit(
            f"❌ aucun modèle computer-use visible pour cette clé.\n"
            f"   Attendu (preview) : {CU_MODEL_HINT}\n"
            f"   → vérifier l'accès preview sur ai.google.dev/gemini-api/docs/computer-use"
        )
    print(f"3/3 ✅ modèle(s) computer-use visible(s) : {cu_models}")
    print("\n🟢 Phase 0 OK — go pour le spike (scripts/cu_spike.py).")


if __name__ == "__main__":
    main()
