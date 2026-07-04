#!/usr/bin/env bash
# Mira — setup Python en une commande. À lancer une fois : bash setup.sh
set -euo pipefail

PY=python3.11
command -v "$PY" >/dev/null 2>&1 || PY=python3
echo "==> Python : $($PY --version)"

if [ ! -d .venv ]; then
  echo "==> Création du venv (.venv)"
  "$PY" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt

echo ""
echo "✅ Prêt."
echo "   source .venv/bin/activate     # activer l'environnement"
echo "   python -m mira.demo           # jouer les 3 beats de démo (mocks)"
echo "   python -m mira.api            # surface API pipeline (HTTP + SSE) sur :8000"
echo "   pytest -q                     # lancer les tests"
echo "   ruff check .                  # lint"
echo ""
echo "Note : le squelette tourne déjà sans rien installer (stdlib seule) :"
echo "   python3.11 -m mira.demo"
