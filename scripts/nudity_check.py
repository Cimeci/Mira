"""Run a real image through the nudity/intent check (Sightengine + Grok).

    python scripts/nudity_check.py <image>

Needs SIGHTENGINE_API_USER / SIGHTENGINE_API_SECRET and XAI_API_KEY in dev.env.
Use a FULL image (nudity lives in the body, not a face crop). A normal photo should
score is_explicit=False — which is the gate correctly rejecting it.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# Load dev.env (gitignored) so the API keys work without exporting them.
_envfile = _ROOT / "dev.env"
if _envfile.exists():
    for _line in _envfile.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _val = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _val.strip())

from mira import prompts, safety, vision  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    image = Path(sys.argv[1]).read_bytes()

    print("== Sightengine nudity-2.1 ==")
    nudity = safety.nudity_scores(image)
    print(json.dumps(nudity, indent=2))
    print(f"explicitness={safety.explicitness(nudity):.3f}  explicit={safety.is_explicit(nudity)}")

    print("\n== Grok intent ==")
    print(vision.ask_grok(image, prompts.load("nudity_intent")))


if __name__ == "__main__":
    main()
