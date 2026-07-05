"""Vision LLM helper (Gemini). Lazy-imports google-genai so importing this module
costs nothing until a call is made. Send face-only crops here, never full bodies.
"""

from __future__ import annotations

import os


def ask_gemini(
    image: bytes,
    prompt: str,
    *,
    model: str = "gemini-2.5-flash",
    mime_type: str = "image/jpeg",
) -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY unset — set it in dev.env (aistudio.google.com/apikey)")
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise RuntimeError("google-genai not installed — `pip install google-genai`") from e

    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model=model,
        contents=[prompt, types.Part.from_bytes(data=image, mime_type=mime_type)],
    )
    return response.text or ""
