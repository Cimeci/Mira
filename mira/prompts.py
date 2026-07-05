"""Prompt registry — loads agentic prompts from Agents/prompts/{name}.md.

Each file is the raw prompt text: the whole file IS the prompt (no markdown scaffolding,
no code fences). Callers inject it by name into the LLM function that needs it, so the
low-level functions (vision.ask_grok, ...) stay prompt-agnostic.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

_DIR = Path(__file__).resolve().parent.parent / "Agents" / "prompts"


@cache
def load(name: str) -> str:
    """Return the prompt in Agents/prompts/{name}.md (whole file, stripped)."""
    return (_DIR / f"{name}.md").read_text(encoding="utf-8").strip()
