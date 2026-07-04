"""Utilitaires de streaming (live view) : encodage des captures pour le SSE."""

from __future__ import annotations

import base64


def data_uri(jpeg_bytes: bytes) -> str:
    """Encode une capture JPEG en data URI, prête à poser dans un <img src>."""
    return "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes).decode("ascii")
