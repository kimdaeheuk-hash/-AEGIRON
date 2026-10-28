# DEMO.md — 3-minute video script (Meta Global AI Developer Hackathon 2026)

Prerequisites before recording: API + web running locally (see README
Quickstart), `META_MODEL_API_KEY` set with credits applied,
`AEGIRON_META_FIRST=on` so the demo deterministically hits Muse Spark.
Total: ≤ 3:00. Show ONLY event-window work (rule).

## 0:00–0:25 — Problem (talking head + dashboard wide shot)

"Epidemic news breaks in dozens of languages every hour. Analysts can't
read it all, and today's tools either miss outbreaks or cry wolf. During
this hackathon we plugged Meta's Muse Spark into our early-warning
engine AEGIRON as a first-class extraction path."

Show: dashboard home at http://localhost:3000 (map + alert list).

## 0:25–1:20 — Live: Muse Spark extracts an outbreak signal (terminal)

Run the one-liner (README "Verify the Meta path") with a fresh sentence,
e.g. a 2026 cholera report line:

```bash
cd epiweather-api
META_MODEL_API_KEY=<key> AEGIRON_META_FIRST=on python -c "
import sys; sys.path.insert(0,'.')
from algorithms import aegiron_model as am
r, a = am.extract_signal_detailed('<fresh outbreak sentence>', source='demo')
print(r.get('ai_provider'), '|', r.get('disease'), '|', r.get('country_iso3'))"
```

Narrate the output: provider `meta_model_api`, structured
disease/country — "Muse Spark just turned a foreign-language headline
into a database-ready outbreak record, tagged with which model made it."

## 1:20–2:10 — Honesty instrumentation (/api/status in browser)

Open http://localhost:8000/api/status → `capability_health` →
`meta_text`: `verified: true`, timestamps, `claim_basis: verified_run`.

"This is the part we're proudest of: the system never claims a
capability from config alone. It only reports Meta as working after it
observes a real successful call — and every stored signal keeps its
`ai_provider` tag so labels stay traceable to the model."

## 2:10–2:45 — Sovereignty gating (terminal, 2 commands)

```bash
AEGIRON_REQUIRE_LOCAL=on  # + same extract call → blocked: true, no HTTP sent
```

"For government and defense buyers, sensitive data must never leave the
country. With one flag, hosted APIs — Meta included — are blocked
*before* sending, while self-hosted models still run. Fail closed, not
fail open."

## 2:45–3:00 — Impact close (dashboard)

"EPIWeather fuses news, weather, mobility, and genomic signals so the
next outbreak is found in days, not months. Built for our world, on
Meta's models." End card: repo URL + track/theme.

## Recording checklist

- [ ] 1080p screen capture, terminal font ≥ 18pt, browser zoom 125%.
- [ ] Terminal shows the REAL call (no pre-baked output); keep the API key
      out of frame (use env var, never `-c` with the key inline on screen).
- [ ] If credits are still pending, record against the mocked test run
      (`pytest tests/test_meta_api.py -q`) and say so on camera — do not
      fake a live call.
- [ ] Upload unlisted; paste the link into README + submission form.
