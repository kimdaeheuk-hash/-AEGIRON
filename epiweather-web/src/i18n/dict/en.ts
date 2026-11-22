import type { Dictionary } from '../types';

// 2026-11-22 개편 사전 — 극지 → 헤임달 → 발할라. 지운 페이지 사전은 커밋 83406e4 에 있음.
export const en: Dictionary = {
  "nav": {
    "polar": "Polar watch",
    "heimdall": "Heimdall",
    "valhalla": "Valhalla",
    "methodology": "Methodology",
    "government": "Government biosecurity",
    "developers": "Developers · API",
    "security": "Security",
    "about": "About",
    "contact": "Contact",
    "product": "Product",
    "company": "Company",
    "dashboard": "Operations view",
    "openMenu": "Open menu",
    "closeMenu": "Close menu",
    "language": "Language"
  },
  "footer": {
    "tagline": "Detect → identify → judge the response.",
    "product": "Product",
    "company": "Company",
    "legal": "Legal",
    "privacy": "Privacy policy",
    "terms": "Terms of use",
    "rights": "All rights reserved.",
    "location": "Busan, South Korea",
    "disclaimer": "AEGIRON does not yet hold a validated track record for early-detection accuracy. Every figure on this site measures the scale of the system, not its predictive performance."
  },
  "home": {
    "metaTitle": "AEGIRON — Polar detection · Heimdall identification · Valhalla response",
    "metaDescription": "Hourly detection of anomalies in polar permafrost regions (Polar), identification of lineage shifts in public genomes (Heimdall), and a verdict on whether national countermeasures cover the threat (Valhalla). For national biosecurity agencies.",
    "eyebrow": "AEGIRON · National biosecurity",
    "title": "Detect → identify → judge the response\nOne chain, nothing else",
    "lead": "We no longer try to watch every disease on Earth. We run a single chain: detect anomalies in polar permafrost every hour, identify pathogen lineage shifts, and judge whether our countermeasures cover the threat.",
    "primaryCta": "Open the operations view",
    "secondaryCta": "For government agencies",
    "chainTitle": "Three links",
    "chainLead": "Each link takes the output of the one before. Only what actually runs today is listed.",
    "stages": [
      {
        "code": "POLAR",
        "name": "Polar watch",
        "role": "Detect",
        "body": "Thawing permafrost is where long-buried pathogens such as anthrax can resurface. We observe weather and local-language news in 8 polar regions every hour.",
        "facts": [
          "8 regions (Yamal, Alaska, Canadian Arctic, Greenland, Svalbard, Antarctic Peninsula and more) observed hourly",
          "Temperature and thaw days are Open-Meteo observations · the anomaly vs normal is computed from a 16-year reanalysis",
          "A watch grade, not an alert — hours that could not be read are kept as undetermined"
        ],
        "href": "polar",
        "linkLabel": "See the polar trend"
      },
      {
        "code": "HEIMDALL",
        "name": "Heimdall",
        "role": "Identify",
        "body": "Records changes of the dominant lineage in public genomic builds (Nextstrain) and computes anomaly indicators for a submitted sequence. Defensive detection only.",
        "facts": [
          "SARS-CoV-2, mpox and RSV-A public builds checked hourly · only dominant-lineage transitions are recorded",
          "Sequence screening (codon usage, CpG, entropy …) on request · API key required",
          "A priority signal, not a verdict — no sequence design or synthesis"
        ],
        "href": "heimdall",
        "linkLabel": "Open the Heimdall section"
      },
      {
        "code": "VALHALLA",
        "name": "Valhalla",
        "role": "Judge the response",
        "body": "For each listed threat, records one row a day on whether registered countermeasures (stockpile, approved products) cover it and whether lineage changes shake that verdict.",
        "facts": [
          "Threat × stockpile × variant verdict written to the ledger daily",
          "Based on public data (WHO-prequalified vaccines, approved products, tenders) · national stockpile levels are not observed",
          "Register stockpile items to compute with them · otherwise the result is marked as illustrative"
        ],
        "href": "valhalla",
        "linkLabel": "Open the Valhalla section"
      }
    ],
    "healthTitle": "Collection status",
    "healthOk": "{ok}/{total} sources of the three layers healthy (measured on the production server)",
    "healthUnknown": "Could not read the production server status (undetermined)",
    "notTitle": "What we do not do",
    "notPoints": [
      "Global outbreak alerts or country risk rankings — removed in the November 2026 overhaul",
      "Claims of outbreak-prediction accuracy — no validated track record",
      "Design, synthesis or optimisation of pathogen sequences — never"
    ]
  },
  "polar": {
    "title": "Polar trend (stored hourly)",
    "lead": "First stored value → latest value per region · temperature (mean daily max) and thaw days are weather observations; Δ (vs the same month’s 10-year mean) is computed · a record is added only when the value changes",
    "span": "About {days} day(s) stored — 30 days not reached yet (stored since 2026-11-15)",
    "undetermined": "{n} record(s) unreadable at their time were left out of the trend (undetermined)",
    "cols": {
      "region": "Region",
      "first": "First stored",
      "latest": "Latest",
      "change": "Change",
      "records": "Records"
    },
    "empty": "No polar values stored yet",
    "unavailable": "Could not read the polar history (undetermined)",
    "apiLabel": "Raw API"
  },
  "pages": {
    "polar": {
      "metaTitle": "Polar watch",
      "metaDescription": "Hourly stored trend of temperature, thaw days and anomaly vs normal in 8 polar regions.",
      "eyebrow": "POLAR · Detect",
      "title": "Polar watch",
      "lead": "Weather anomalies in permafrost regions, observed and stored hourly · a watch grade, not an alert",
      "blocks": []
    },
    "about": {
      "metaTitle": "About",
      "metaDescription": "AEGIRON — national biosecurity technology focused on polar detection, genomic identification and countermeasure verdicts.",
      "eyebrow": "ABOUT",
      "title": "AEGIRON",
      "lead": "A one-person technology start-up in Busan · national biosecurity agencies are the first customer",
      "blocks": [
        {
          "title": "Why we narrowed",
          "body": "Until November 2026 AEGIRON collected disease signals from everywhere. The wider the scope, the thinner the expertise, and external reviews were poor. We kept one chain — detect (Polar) → identify (Heimdall) → judge the response (Valhalla) — and deleted the rest."
        },
        {
          "title": "Principles",
          "points": [
            "**Measured, estimated and proxy values are never mixed** — every view says which is which",
            "**Three states** — success / failure / undetermined. What we did not see is never written as zero or normal",
            "**Defensive only** — no function that creates or modifies pathogens"
          ]
        }
      ],
      "cta": {
        "title": "Adoption and partnership",
        "body": "Reviews by national and regional biosecurity agencies are welcome",
        "label": "Contact",
        "href": "contact"
      }
    },
    "methodology": {
      "metaTitle": "Methodology",
      "metaDescription": "How the polar watch score, the Heimdall variant ledger and the Valhalla match verdict are computed, and their limits.",
      "eyebrow": "METHODOLOGY",
      "title": "Methodology",
      "lead": "What each link measures, and what it does not",
      "blocks": [
        {
          "title": "Polar watch",
          "kicker": "POLAR",
          "tone": "sky",
          "points": [
            "Temperature (mean daily max) and thaw days = Open-Meteo observations",
            "Anomaly vs normal = **computed** against the same month’s 16-year reanalysis mean",
            "Share of local-language (ru/en/no) news keywords = **proxy** · not a confirmation",
            "The watch score is a grade, not an alert · hours without weather data are undetermined"
          ],
          "note": "Limits: each of the 8 regions is a single representative point · the causal link from thaw to pathogen exposure is a hypothesis"
        },
        {
          "title": "Heimdall",
          "kicker": "HEIMDALL",
          "tone": "violet",
          "points": [
            "Reads the dominant lineage and its share over the last 60 days from public Nextstrain builds",
            "Only cycles where the dominant lineage changed are recorded as transitions · nothing is written when data is missing",
            "Screening indicators (CAI, CpG, entropy, local anomalies) are **priority signals**, not verdicts"
          ],
          "note": "Limits: inherits the delays and biases of public sequence submission"
        },
        {
          "title": "Valhalla",
          "kicker": "VALHALLA",
          "tone": "forest",
          "points": [
            "For each threat, coverage is judged from the target pathogens and declared efficacy of registered countermeasures",
            "Variant-ledger flags are written next to the verdict",
            "National stockpile levels and variant-specific efficacy are not public and are not observed"
          ],
          "note": "Limits: without registered stockpile items the computation uses illustrative data, and the response says so"
        }
      ]
    },
    "government": {
      "metaTitle": "Government biosecurity",
      "metaDescription": "Polar detection, genomic identification and countermeasure verdicts for national biosecurity agencies.",
      "eyebrow": "GOVERNMENT",
      "title": "For national biosecurity agencies",
      "lead": "National biosecurity agencies are our first customer · detect → identify → judge the response in one view",
      "blocks": [
        {
          "title": "What an agency gets",
          "items": [
            {
              "title": "Early polar observation",
              "body": "An hourly record of weather anomalies in 8 permafrost regions",
              "meta": "Polar"
            },
            {
              "title": "Lineage transition ledger",
              "body": "A ledger of when the dominant lineage changed in public genomes",
              "meta": "Heimdall"
            },
            {
              "title": "Countermeasure gap verdict",
              "body": "One row a day per threat on whether registered countermeasures cover it",
              "meta": "Valhalla"
            }
          ]
        },
        {
          "title": "How to adopt",
          "points": [
            "Review immediately through the public API",
            "Register the agency stockpile to compute verdicts with it (key required)",
            "A configuration that never sends sensitive data to external APIs is possible"
          ]
        },
        {
          "title": "Honesty notice",
          "accent": true,
          "points": [
            "No track record of prediction accuracy",
            "A watch grade is not an alert · response decisions remain with the agency"
          ]
        }
      ],
      "cta": {
        "title": "Pilot review",
        "body": "Review material and a demonstration for agencies",
        "label": "Contact",
        "href": "contact"
      }
    },
    "security": {
      "metaTitle": "Security and data governance",
      "metaDescription": "Access control, high-risk program control, privacy principles, data sovereignty and secret management.",
      "eyebrow": "SECURITY & GOVERNANCE",
      "title": "Security and data governance",
      "lead": "Who can change what, how sensitive functions are controlled, where data goes — disclosed as implemented",
      "blocks": [
        {
          "title": "Access control",
          "kicker": "ACCESS CONTROL",
          "tone": "indigo",
          "specs": [
            {
              "label": "Total API",
              "value": "25 endpoints"
            },
            {
              "label": "Authentication required",
              "value": "7 — state-changing, costly and high-risk functions"
            },
            {
              "label": "Method",
              "value": "X-API-Key header · multiple labelled keys · constant-time comparison"
            },
            {
              "label": "With no key configured",
              "value": "All write APIs disabled — never left open"
            }
          ]
        },
        {
          "title": "High-risk program control",
          "kicker": "HEIMDALL · VALHALLA",
          "tone": "violet",
          "points": [
            "Sequence screening and stockpile registration require authentication · every call is logged by key label",
            "HEIMDALL is **defensive detection only** · no sequence design, synthesis, optimisation or evasion function"
          ]
        },
        {
          "title": "Privacy principles",
          "kicker": "PRIVACY",
          "tone": "teal",
          "points": [
            "What is collected is public weather, genomic and procurement data · no individual patient data",
            "The website and operations view run without login, advertising or visitor tracking"
          ]
        },
        {
          "title": "Secrets and operational integrity",
          "kicker": "INTEGRITY",
          "tone": "sky",
          "items": [
            {
              "title": "Secrets",
              "body": "API keys and credentials live only in production environment variables · never in the repository or documents"
            },
            {
              "title": "Deployment gate",
              "body": "Only code that passes all 614 automated tests reaches production"
            },
            {
              "title": "Silent-failure watch",
              "body": "Source health recorded every cycle · liveness checked hourly from outside (GitHub Actions)"
            }
          ]
        }
      ],
      "cta": {
        "title": "Request security review material",
        "body": "Configuration and control documentation for an agency security review",
        "label": "Contact",
        "href": "contact"
      }
    },
    "developers": {
      "metaTitle": "Developers · API",
      "metaDescription": "AEGIRON REST API — 25 endpoints, JSON responses, X-API-Key authentication, OpenAPI documentation.",
      "eyebrow": "DEVELOPERS",
      "title": "Developers · API",
      "lead": "The single source of every figure in the operations view is the REST API",
      "blocks": [
        {
          "title": "Basics",
          "kicker": "BASICS",
          "tone": "sky",
          "specs": [
            {
              "label": "Base URL",
              "value": "https://epiweather-api-production.up.railway.app"
            },
            {
              "label": "Format",
              "value": "REST · JSON"
            },
            {
              "label": "Authentication",
              "value": "Reads public · writes/high-risk X-API-Key"
            },
            {
              "label": "Interactive docs",
              "value": "/docs (OpenAPI)"
            }
          ]
        },
        {
          "title": "Key endpoints",
          "kicker": "QUICK START",
          "tone": "teal",
          "items": [
            {
              "title": "Polar watch",
              "body": "Watch score, baseline and trend for 8 regions",
              "meta": "GET /api/polar-watch"
            },
            {
              "title": "Polar history",
              "body": "Hourly stored observation series",
              "meta": "GET /api/observations/history?layer=polar"
            },
            {
              "title": "Variant ledger",
              "body": "Dominant-lineage transitions in public genomes",
              "meta": "GET /api/variant-ledger"
            },
            {
              "title": "Match ledger",
              "body": "Daily threat × stockpile × variant verdicts",
              "meta": "GET /api/valhalla/match-ledger"
            },
            {
              "title": "Operations status",
              "body": "Source health, scheduler and reference snapshots",
              "meta": "GET /api/status"
            }
          ]
        }
      ],
      "cta": {
        "title": "Integration keys",
        "body": "Per-agency API keys for write and high-risk functions",
        "label": "Contact",
        "href": "contact"
      }
    },
    "contact": {
      "metaTitle": "Contact",
      "metaDescription": "How to reach AEGIRON.",
      "eyebrow": "CONTACT",
      "title": "Contact",
      "lead": "You can review the whole system without booking a demo. If, after reviewing it, you have questions or a proposal for collaboration, please reach us below.",
      "blocks": [
        {
          "title": "Details",
          "items": [
            {
              "title": "Email",
              "body": "kimdaeheuk@gmail.com",
              "meta": "The fastest route"
            },
            {
              "title": "Location",
              "body": "Busan, South Korea",
              "meta": "KST (UTC+9)"
            }
          ]
        },
        {
          "title": "Especially welcome",
          "points": [
            "**Corrections** — tell us about errors in our methodology or figures and we will verify and reflect them.",
            "**Connections to field organisations** — a route into real surveillance networks is our most important next step.",
            "**Pilot discussions** — reinsurers, governments, international bodies and field organisations are all welcome."
          ]
        }
      ]
    },
    "privacy": {
      "metaTitle": "Privacy policy",
      "metaDescription": "Privacy policy for the AEGIRON website.",
      "eyebrow": "LEGAL",
      "title": "Privacy policy",
      "lead": "This site does not require visitors to log in and does not collect personal information.",
      "blocks": [
        {
          "title": "What we do not collect",
          "points": [
            "There is no sign-up or login, so no account information is collected.",
            "This site uses no advertising or visitor-analytics tracking tools.",
            "Viewing the dashboard requires no personally identifying information."
          ]
        },
        {
          "title": "External services",
          "body": "The introduction video on the home page is embedded in YouTube’s privacy-enhanced mode; YouTube’s policies apply once it is played. Fonts are loaded from Google Fonts and jsDelivr, so those services may record access data such as IP addresses."
        },
        {
          "title": "When you contact us",
          "body": "If you email us, the content and your address are used only to reply and are never shared with third parties."
        },
        {
          "title": "Changes",
          "body": "If this policy changes, this page will be updated."
        }
      ]
    },
    "terms": {
      "metaTitle": "Terms of use",
      "metaDescription": "Terms for using the AEGIRON website and its public data.",
      "eyebrow": "LEGAL",
      "title": "Terms of use",
      "lead": "The conditions that apply when you use this site and the public dashboard.",
      "blocks": [
        {
          "title": "Nature of the information provided",
          "accent": true,
          "points": [
            "Information on this site is **for reference only** and is not provided as a basis for medical, public-health or investment decisions.",
            "Forecast and scenario figures are **estimates under model assumptions** — neither measurements nor guarantees.",
            "AEGIRON does not yet hold a validated track record for early-detection accuracy.",
            "AEGIRON accepts no liability for the consequences of decisions based on this information."
          ]
        },
        {
          "title": "Data sources",
          "body": "This system collects and processes public material from bodies such as the WHO and the CDC. Copyright and terms of use for the original material remain with each body. Processed figures may differ from the originals, so always consult the originating body’s material when an official citation is needed."
        },
        {
          "title": "Availability",
          "body": "The public dashboard may be suspended or changed without notice."
        }
      ]
    }
  },
  "api": {
    "tableTitle": "All endpoints",
    "tableLead": "Every endpoint of the production API, grouped by function. The lock marks endpoints that need an X-API-Key.",
    "authYes": "Key required",
    "authNo": "Public",
    "tags": {
      "GAI": "Polar watch",
      "Phase2": "Heimdall · genomic lineages",
      "후향 검증": "Heimdall · variant ledger",
      "Stage 0: 합성위협 탐지": "Heimdall · synthetic-threat detection and sequence screening",
      "Stage 8: 바이오방어": "Valhalla · countermeasure verdicts",
      "시스템": "System · operations status"
    }
  },
  "common": {
    "siteName": "AEGIRON"
  }
};
