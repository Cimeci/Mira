#!/usr/bin/env bash
# Mira — scaffold Next.js + tooling qualité + pre-commit, en une commande.
# À lancer UNE fois, après avoir choisi le track (voracité du hackathon oblige).
# Usage : bash setup.sh
set -euo pipefail

if [ -f package.json ]; then
  echo "package.json existe déjà → scaffold déjà fait. J'installe juste les deps."
  pnpm install
  exit 0
fi

echo "==> Scaffold Next.js (TS + Tailwind + App Router + ESLint) dans un temp, puis merge"
TMP="$(mktemp -d)"
pnpm create next-app@latest "$TMP/app" \
  --typescript --tailwind --app --eslint --src-dir \
  --import-alias "@/*" --use-pnpm --no-turbopack --yes

# Merge sans écraser nos docs/config déjà en place
rsync -a \
  --exclude='.git' --exclude='README.md' --exclude='LICENSE' \
  --exclude='.gitignore' --exclude='.editorconfig' \
  --exclude='.prettierrc.json' --exclude='.prettierignore' \
  "$TMP/app/" ./
rm -rf "$TMP"

echo "==> Tooling qualité"
pnpm add -D prettier prettier-plugin-tailwindcss eslint-config-prettier husky lint-staged

echo "==> Scripts package.json (check / format)"
node - <<'JS'
const fs = require('fs');
const p = JSON.parse(fs.readFileSync('package.json', 'utf8'));
p.scripts = {
  ...p.scripts,
  check: 'tsc --noEmit && eslint . && prettier --check .',
  format: 'prettier --write .',
  prepare: 'husky',
};
p['lint-staged'] = {
  '*.{ts,tsx,js,jsx}': ['eslint --fix', 'prettier --write'],
  '*.{json,css,md}': ['prettier --write'],
};
fs.writeFileSync('package.json', JSON.stringify(p, null, 2) + '\n');
JS

echo "==> Pre-commit hook (husky + lint-staged)"
pnpm exec husky init
printf 'pnpm exec lint-staged\n' > .husky/pre-commit

echo ""
echo "✅ Prêt. Vérifs :"
echo "   pnpm dev      → http://localhost:3000"
echo "   pnpm check    → typecheck + lint + format"
echo "   git commit    → formate/lint les fichiers stagés automatiquement"
