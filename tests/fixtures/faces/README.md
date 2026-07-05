# Face recognition test fixtures

Drop three photos here to enable `tests/test_face_match.py::test_real_face_recognition`
(skipped until all three exist and `insightface` is installed — i.e. it runs on the GPU VM):

- `reference.jpg`   — the victim's reference photo (what gets enrolled)
- `same_person.jpg` — the **same** person, a *different* photo → must MATCH
- `other_person.jpg`— a **different** person → must NOT match

Optional:
- `no_face.jpg` — an image with no detectable face → `NoFaceDetectedError`

These are **not** committed (gitignored) — use your own faces or a public face set.
Tune the decision boundary with `MIRA_MATCH_THRESHOLD` if your set needs it.
