"""Vision LLM helpers (Gemini + Grok).

Send face-only crops here when identity isn't the point — only the face, never a nude
body, leaves the system. Grok (xAI) is more permissive than Gemini on explicit-content
classification, so it's the better tool for a nudity/intent check; Gemini often refuses.
"""

from __future__ import annotations

import base64
import os

import httpx


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


def ask_grok(
    image: bytes,
    prompt: str,
    *,
    model: str = "grok-4.3",  # xAI vision model; swap if your key exposes another
    mime_type: str = "image/jpeg",
) -> str:
    """Ask xAI Grok about an image. OpenAI-compatible chat/completions with a base64
    image; needs XAI_API_KEY (console.x.ai)."""
    key = os.getenv("XAI_API_KEY")
    if not key:
        raise RuntimeError("XAI_API_KEY unset — set it in dev.env (console.x.ai)")
    data_url = f"data:{mime_type};base64,{base64.b64encode(image).decode()}"
    resp = httpx.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"] or ""
