# Backend image for the Nebius VM — the FastAPI app that drives the whole pipeline
# (locator/Computer Use, analyzer/ArcFace, notifier). This branch is the next main,
# so the entrypoint is ours.
#
# CPU base here (onnxruntime CPU). For the GPU VM, swap to an nvidia/cuda base image
# and `onnxruntime-gpu` for faster ArcFace; the app code is unchanged.
FROM python:3.11-slim

# System libs: opencv needs libGL/libglib; Chromium runtime deps come via playwright.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# Base deps + the face stack (insightface/ArcFace) + the Computer Use browser.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir insightface onnxruntime opencv-python-headless \
    && python -m playwright install --with-deps chromium

COPY mira/ ./mira/
COPY supabase/ ./supabase/

ENV PORT=8000
EXPOSE 8000
CMD ["uvicorn", "mira.api:app", "--host", "0.0.0.0", "--port", "8000"]
