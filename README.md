## Sigil Solver

High-performance slide-captcha solver powered by FastAPI, Ultralytics YOLO, ONNX Runtime, and PyTorch.

### Features

-  Robust FastAPI service with DI via Dishka
-  Single endpoint to solve slide-style captchas
-  GPU acceleration on Linux/Windows (CUDA) when available; optimized CPU paths otherwise
-  Production-friendly logging and error handling
-  OpenAPI/Scalar docs included

### Requirements

-  Python 3.10–3.11
-  macOS, Linux, or Windows
-  Optional: NVIDIA GPU + CUDA drivers for acceleration on Linux/Windows

### Quickstart

1. Clone the repository

```bash
git clone <repository-url>
cd sigil-solver
```

2. Create a virtual environment and install dependencies (recommended: uv)

```bash
pipx install uv || pip install uv
uv venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
uv sync
```

3. Run the API

-  Fastest way (ASGI):

```bash
uv run uvicorn sigil.main.api.native:app --host 0.0.0.0 --port 8000
```

-  Alternatively (CLI wrapper):

```bash
uv run python -c "from sigil.main.cli.app import run_cli; run_cli()" api --host 0.0.0.0 --port 8000
```

4. Explore docs

-  Scalar UI: http://localhost:8000/scalar
-  OpenAPI JSON: http://localhost:8000/docs

### Configuration

The app uses `pydantic-settings` with the `SIGIL_` prefix. You can set variables in your environment or a `.env` file at the project root.

Available keys (nested config uses double underscores):

-  `SIGIL_SECRET_KEY`: Secret key (default: `secret_key`)
-  `SIGIL_DEBUG`: `true`/`false` to enable debug mode (default: `false`)
-  `SIGIL_OPENAI__API_KEY`: Optional OpenAI API key
-  `SIGIL_OPENAI__MODEL`: Optional OpenAI model (default: `o3`)
-  `SIGIL_ANTHROPIC__API_KEY`: Optional Anthropic API key
-  `SIGIL_ANTHROPIC__MODEL`: Optional Anthropic model (default: `claude-opus-4-1-20250805`)

Example `.env`:

```env
SIGIL_DEBUG=true
SIGIL_SECRET_KEY=change_me
SIGIL_OPENAI__API_KEY=sk-xxxxx
SIGIL_ANTHROPIC__API_KEY=anthropic-xxxxx
```

### API Overview

Base URL: `http://localhost:8000`

-  GET `/` → Service status

   -  Response: `{ "success": true, "msg": "running" }`

-  GET `/health` → Health check

   -  Response: `{ "status": "ok" }`

-  GET `/scalar` → Interactive API docs (Scalar UI)

-  POST `/api/v1/captchas/slide` → Solve slide captcha
   -  Request body fields (JSON):
      -  `puzzle_image_b64`: Base64 data URI or raw base64 string of the puzzle image (optional)
      -  `puzzle_image_url`: URL to the puzzle image (optional)
      -  `piece_image_b64`: (reserved) Base64 of the slider piece (optional)
      -  `piece_image_url`: (reserved) URL of the slider piece (optional)
      -  `shrink_size`: Optional shrink size (default: `340.0`)
   -  Exactly one of `puzzle_image_b64` or `puzzle_image_url` is required.
   -  Response body:
      -  `status`: `successful` or `failed`
      -  `x`: float, the estimated x-offset where the piece should slide

#### cURL examples

Using an image URL:

```bash
curl -X POST http://localhost:8000/api/v1/captchas/slide \
  -H 'Content-Type: application/json' \
  -d '{
        "puzzle_image_url": "https://example.com/captcha.jpg"
      }'
```

Using base64 (data URI or raw base64):

```bash
BASE64=$(base64 -w 0 path/to/captcha.jpg)  # macOS: base64 path/to/captcha.jpg | tr -d '\n'
curl -X POST http://localhost:8000/api/v1/captchas/slide \
  -H 'Content-Type: application/json' \
  -d "{ \"puzzle_image_b64\": \"$BASE64\" }"
```

Example response:

```json
{
   "data": {
      "status": "successful",
      "x": 132.4
   },
   "meta": {}
}
```

### How it works

-  `sigil.services.recognizer.RecognizerService` loads two ONNX YOLO models from `sigil/models/yolo/`.
-  The service predicts the likely gap location and returns an x-offset.
-  CUDA is used automatically if available; otherwise, it falls back to CPU.

### Development

Run the server in reload mode:

```bash
uv run uvicorn sigil.main.api.native:app --reload --host 0.0.0.0 --port 8000
```

Run tests:

```bash
uv run pytest -q
```

Code style and tooling:

-  Formatter: black, isort
-  Lint: ruff, flake8, mypy
-  Pre-commit hooks are available in the dev group

### Troubleshooting

-  Torch/ONNX install issues:
   -  macOS arm64 uses `onnxruntime-silicon` automatically; ensure Python 3.10–3.11.
   -  Linux/Windows with NVIDIA GPU: ensure CUDA toolkits/drivers compatible with PyTorch 2.2.2.
-  Large model memory usage:
   -  Set `ENVIRONMENT=production` to avoid verbose stderr inferences.
   -  Reduce `imgsz` or confidence thresholds in `RecognizerService._predict` if customizing.
-  HTTP 400 when downloading images:
   -  Ensure the URL is reachable and returns an `image/*` content type.

### Project Structure (selected)

```
sigil/
  core/                 # settings, logging, DI providers
  main/api/             # FastAPI app factory and native app entry
  main/cli/             # Typer CLI factory
  presentation/         # routers, views, responses, exceptions
  schemas/              # request/response models
  services/             # Recognizer service (YOLO + ONNX)
  models/yolo/          # ONNX model files
```

### License

This project is licensed under the terms of the MIT License. See `LICENSE` for details.
