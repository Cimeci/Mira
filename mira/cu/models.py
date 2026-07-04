"""Contrats internes de la couche CU. Séparés des contrats gelés (`mira/types.py`)
car ils sont propres à ma lane : je peux les faire évoluer sans impacter l'équipe.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScrapedImage:
    """Une image trouvée sur la page cible."""

    url: str                    # URL absolue de l'image
    alt: str = ""               # texte alternatif (indice de contexte)
    width: int | None = None    # dimension naturelle en px (None si inconnue)
    height: int | None = None
    note: str = ""              # description faite par l'agent ("décris l'image")


@dataclass
class ScrapeResult:
    """Sortie d'un run de scraping. Alimente la page résultats."""

    source_url: str
    images: list[ScrapedImage] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)   # trace des actions de l'agent
    screenshot_url: str | None = None                # capture full-page (preuve visuelle)
    driver: str = "playwright"        # "playwright" | "gemini-cu"
    elapsed_s: float = 0.0
    error: str | None = None          # message si le run a échoué (jamais avalé en silence)

    @property
    def count(self) -> int:
        return len(self.images)
