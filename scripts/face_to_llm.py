"""Extract every face from an image (face only, no body) and ask Gemini about each.

    python scripts/face_to_llm.py <image> ["your prompt"]

Saves each crop next to the run so you can eyeball that it's face-only. Needs
insightface installed and GEMINI_API_KEY set.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))  # run-by-path puts scripts/ on the path, not the repo root

# Load dev.env (gitignored) so GEMINI_API_KEY etc. work without exporting them.
_envfile = _ROOT / "dev.env"
if _envfile.exists():
    for _line in _envfile.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _val = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _val.strip())

from mira.providers.face_local import InsightFaceProvider  # noqa: E402
from mira.vision import ask_gemini  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    image = Path(sys.argv[1]).read_bytes()
    prompt = sys.argv[2] if len(sys.argv) > 2 else "Describe this face in one sentence."

    faces = InsightFaceProvider().crop_faces(image)
    print(f"detected {len(faces)} face(s)")
    for i, crop in enumerate(faces):
        out = Path(f"face_{i}.jpg")
        out.write_bytes(crop)
        print(f"\n[face {i}] saved {out} ({len(crop)} bytes)")
        print(ask_gemini(crop, prompt))


if __name__ == "__main__":
    main()
