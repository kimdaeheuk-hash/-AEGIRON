# EPIWeather (역병예보) + AEGIRON — Epidemic Early Warning on Meta Model API

Infectious-disease early-warning system: a FastAPI inference engine
(`epiweather-api`) plus a Next.js dashboard (`epiweather-web`). It fuses
news, weather, mobility, genomic, and deforestation signals into outbreak
alerts with honest provenance on every record.

Submitted to the **Meta Global AI Developer Hackathon 2026**
(Oct 26 – Nov 4, 2026).

- Track (proposed): **Indie Developer**
- Theme (proposed): **Build for Your World** — Meta's models in the
  public-health domain, solving an outbreak-detection problem firsthand.
- Demo video (3 min): _link added before submission_
- Live demo: run locally (see Quickstart) — no hosted demo claimed.

## Built during the event (Oct 26 – Nov 4)

Per the event rule that the demo shows event-window work, the submission
centers on what changed in the window:

1. **Meta Model API extraction path (Oct 28, this branch's headline work)**
   - `epiweather-api/algorithms/meta_api.py` (new): single source of truth
     for the Meta Model API convention — default `muse-spark-1.3` on
     `https://api.meta.ai/v1` (OpenAI-compatible chat/completions).
   - `epiweather-api/algorithms/aegiron_model.py`: extraction order is now
     NIM → **Meta** → local → Claude fallback; `AEGIRON_META_FIRST=on`
     forces Meta first for the demo.
   - Every extracted signal is tagged `ai_provider=meta_model_api` (+
     `data_sovereign` flag); calls are observed in the capability ledger
     and surfaced on `/api/status`.
   - `epiweather-api/tests/test_meta_api.py` (new): 17 tests, all mocked
     (no outbound HTTP per repo policy).
2. **WHO outbreak-declaration country evidence (#109, #111, Oct 26–27)**
   - `who_don_declarations.py` + `country_resolve.py`: declaration
     announcements now carry resolved country evidence with logged basis.

## How Meta's AI is used (beyond a basic integration)

- **Muse Spark does production extraction**, not a side demo: multilingual
  news text → structured outbreak records (disease, country, signal type)
  through the same prompt/schema as every other backend, so quality is
  comparable across providers.
- **Honest provider tagging**: each stored signal records which model made
  the label (`extracted_signals.ai_provider`), and `/api/status` separates
  "configured" from "recently observed working" — a claim this repo was
  built around after real incidents.
- **Sovereignty gating**: Meta-hosted inference is correctly marked
  non-sovereign; with `AEGIRON_REQUIRE_LOCAL=on`, sensitive data is blocked
  *before* leaving, and self-hosted OpenAI-compatible bases count as
  sovereign automatically.
- **Unguessable-parameter discipline**: the Meta path deliberately does
  *not* send NVIDIA-only parameters the team never validated against Meta.

## Quickstart

Requirements: Python 3.11+, Node 20+, a Meta Model API key
([dev.meta.ai](https://dev.meta.ai/) → API keys).

```bash
# 1. API
cd epiweather-api
pip install -r requirements.txt
cp .env.example .env   # then set META_MODEL_API_KEY (and data-source keys)
uvicorn main:app --port 8000   # Swagger UI: http://localhost:8000/docs

# 2. Web (new terminal)
cd epiweather-web
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                  # http://localhost:3000
```

Key env vars (API `.env`):

| Variable | Purpose |
|---|---|
| `META_MODEL_API_KEY` | Meta Model API key (`MODEL_API_KEY` also accepted) |
| `META_MODEL_API_MODEL` | Override (default `muse-spark-1.3`) |
| `AEGIRON_META_FIRST` | `on` = try Meta before NIM (demo forcing) |
| `EPIWEATHER_API_KEY` | Required: protects POST endpoints (fail-closed 503) |

## Verify the Meta path (1 minute, live)

```bash
cd epiweather-api
META_MODEL_API_KEY=<key> python -c "
import sys; sys.path.insert(0,'.')
from algorithms import aegiron_model as am
r, a = am.extract_signal_detailed('DRC 에볼라 신규발생', source='demo')
print(r.get('ai_provider'), '|', r.get('disease'), '|', r.get('country_iso3'))"
# expected: meta_model_api | 에볼라 | COD
```

Then open `http://localhost:8000/api/status` → `capability_health` →
`meta_text` shows `verified: true` after a real call.

## Layout

- `epiweather-api/` — FastAPI service: `main.py`, `collector.py`, `db.py`,
  `algorithms/` (inference layers), `tests/` (2389 tests, mocked HTTP).
- `epiweather-web/` — Next.js 16 dashboard (i18n, Leaflet maps).
- `epiweather-handoff/` — engine sources reused by the API.
- `docs/` — ops notes. `DEMO.md` — 3-minute demo script.

## Test status

- New Meta path: 17/17 pass; affected area (AEGIRON/NIM/ledger/diagnostics):
  220/220 pass.
- Full API suite: 2389 tests collected. `test_main_endpoints.py` needs
  localhost sockets, blocked in some sandboxes (fails identically without
  this change — environmental, not a regression).
