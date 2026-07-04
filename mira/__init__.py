"""Mira — agent assistif consent-first (retrait de deepfakes non consentis, droit EU).

Squelette de hackathon : le pipeline Mandate -> Locate -> Analyze -> Notify tourne
end-to-end AVEC DES MOCKS (aucun réseau, aucun contenu réel). Chaque lane remplace
le mock de son stage par le vrai, derrière la même interface (voir mira/types.py).
"""

__all__ = ["types", "config", "mandate", "locator", "analyzer", "notifier", "orchestrator"]
