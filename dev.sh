#!/usr/bin/env bash
# Mira — lance TOUTES les surfaces locales en une commande : bash dev.sh
#   API pipeline (HTTP+SSE)  → http://127.0.0.1:${MIRA_API_PORT:-8000}   (mira/api.py)
#   Locator CU (live view)   → http://127.0.0.1:${MIRA_WEB_PORT:-8001}   (mira/web)
#   Frontend (Next.js)       → http://127.0.0.1:${FRONTEND_PORT:-3000}   (frontend/)
#   face-verifier (Node)     → http://127.0.0.1:${FACE_VERIFIER_PORT:-3001}
#                               (démarré seulement si services/face-verifier/node_modules existe)
# Ctrl+C arrête tout proprement.
set -euo pipefail
cd "$(dirname "$0")"

PY=.venv/bin/python
if [ ! -x "$PY" ]; then
  echo "❌ .venv absent — lance d'abord : bash setup.sh" >&2
  exit 1
fi

API_PORT="${MIRA_API_PORT:-8000}"
WEB_PORT="${MIRA_WEB_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
FACE_PORT="${FACE_VERIFIER_PORT:-3001}"

# Gate G-7 : en dev/démo, le présentateur laisse la notice à l'écran le temps de
# la commenter — sans ça le gate s'auto-annule (fail-closed) au bout de 120 s et
# « approve » renvoie 409. MIRA_DEMO_MODE=1 plancher le timeout à 15 min.
export MIRA_DEMO_MODE="${MIRA_DEMO_MODE:-1}"

START_FACE=0
[ -d services/face-verifier/node_modules ] && START_FACE=1
START_FRONTEND=0
[ -d frontend/node_modules ] && START_FRONTEND=1

# Fail fast : un port déjà occupé donnerait un uvicorn qui meurt en silence au
# milieu des logs des autres services.
ports_to_check=("$API_PORT" "$WEB_PORT")
[ "$START_FRONTEND" = 1 ] && ports_to_check+=("$FRONTEND_PORT")
[ "$START_FACE" = 1 ] && ports_to_check+=("$FACE_PORT")
for port in "${ports_to_check[@]}"; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "❌ Le port $port est déjà occupé (lsof -i :$port pour voir par qui)." >&2
    exit 1
  fi
done

# Tue un process ET ses descendants (npm garde son serveur node en enfant :
# tuer npm seul laisserait un node zombie accroché au port).
kill_tree() {
  local child
  for child in $(pgrep -P "$1" 2>/dev/null); do kill_tree "$child"; done
  kill "$1" 2>/dev/null || true
}

pids=()
cleanup() {
  trap - INT TERM EXIT
  local pid
  for pid in "${pids[@]}"; do kill_tree "$pid"; done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# Log files
LOG_DIR=".dev-logs"
mkdir -p "$LOG_DIR"

# API
MIRA_API_PORT="$API_PORT" "$PY" -m mira.api > "$LOG_DIR/api.log" 2>&1 &
pids+=($!)

# Web (locator CU)
MIRA_WEB_PORT="$WEB_PORT" "$PY" -m mira.web > "$LOG_DIR/web.log" 2>&1 &
pids+=($!)

# Frontend
FRONTEND_URL="(non démarré)"
if [ "$START_FRONTEND" = 1 ]; then
  (cd frontend && PORT="$FRONTEND_PORT" npm run dev > "../$LOG_DIR/frontend.log" 2>&1) &
  pids+=($!)
  FRONTEND_URL="http://127.0.0.1:$FRONTEND_PORT"
else
  echo "[frontend] node_modules absent — service sauté. Pour l'activer :"
  echo "[frontend]   cd frontend && npm install"
fi

# Face verifier
FACE_URL="(non démarré)"
if [ "$START_FACE" = 1 ]; then
  (cd services/face-verifier && PORT="$FACE_PORT" npm run --silent dev:local > "../../$LOG_DIR/face.log" 2>&1) &
  pids+=($!)
  FACE_URL="http://127.0.0.1:$FACE_PORT"
else
  echo "[face] node_modules absent — service sauté. Pour l'activer :"
  echo "[face]   cd services/face-verifier && npm install"
fi

sleep 2
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Mira — tout tourne (Ctrl+C pour tout arrêter)"
echo "  API pipeline (SSE)   http://127.0.0.1:$API_PORT   (docs/API.md)"
echo "  Locator CU (live)    http://127.0.0.1:$WEB_PORT"
echo "  Frontend (Next.js)   $FRONTEND_URL"
echo "  face-verifier        $FACE_URL"
echo "══════════════════════════════════════════════════════════"
echo ""
echo "Logs: tail -f $LOG_DIR/<service>.log"
echo ""

wait