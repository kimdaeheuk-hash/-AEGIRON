import type { ExtraDict } from '../types';

/** Live operations, verification and national pages (English). Measured values only. */
export const extraPagesEn: ExtraDict['pages'] = {
  live: {
    metaTitle: 'Live operations — what AEGIRON is doing right now',
    metaDescription: 'Screens captured from AEGIRON’s running dashboard and live operational figures — what it is collecting, where it is looking and what it has raised as an alert.',
    eyebrow: 'LIVE OPERATIONS',
    title: 'This is AEGIRON, running',
    lead: 'Not a description — the operational screens and the operational numbers. The figures and lists below are re-read from the production server every few minutes, and the images are captured from the dashboard as it runs.',
    blocks: [],
    cta: {
      title: 'Open the same screen yourself',
      body: 'The production dashboard opens with no login, updating in real time just like the captures above.',
      label: 'Open the live dashboard',
      href: '/dashboard',
    },
  },

  record: {
    metaTitle: 'Public forecast ledger — sealed forecasts and their scores',
    metaDescription: 'AEGIRON publishes its forecasts exactly as they were made — blockchain timestamp proofs, automatic scoring against official declarations, and the lead-time ledger, all from live data.',
    eyebrow: 'TRACK RECORD',
    title: 'Public forecast ledger',
    lead: 'Trust in early warning does not come from claims. AEGIRON seals a forecast when it is made and scores it automatically, every day, against the official declarations that follow. Hits, misses and pending calls are never deleted — they stay in this ledger as they are.',
    blocks: [],
    cta: {
      title: 'Curious how scoring works?',
      body: 'What counts as ground truth — and what never does — is set out on the validation page.',
      label: 'See the validation framework',
      href: 'transparency',
    },
  },

  korea: {
    metaTitle: 'AEGIRON for Korea — early warning for an importing country',
    metaDescription: 'Import timing of overseas outbreaks and risk by port of entry, domestic notifiable-disease surveillance, countermeasure production sovereignty, national procurement watch and data sovereignty — AEGIRON from Korea’s point of view.',
    eyebrow: 'FOR KOREA',
    title: 'AEGIRON for Korea',
    lead: 'For most emerging infections, Korea is not where an outbreak starts but where it arrives. So the question is less “where did it start” than “when, through which gateway, and with what can we stop it”. AEGIRON was designed around that question.',
    photo: {
      src: '/media/live/model-global-inflow.jpg',
      alt: 'AEGIRON dashboard screen for global import detection — an air-network map from the origin to Korea',
      caption: 'The global import detection screen of the running dashboard (capture). It estimates arrival timing and the port of entry from an origin to Korea; the figures are a model scenario under the chosen assumptions.',
      credit: 'AEGIRON operational screen',
      sourceUrl: '/dashboard',
    },
    blocks: [
      {
        title: 'Overseas outbreak → domestic import',
        kicker: 'INBOUND',
        tone: 'indigo',
        body: 'From the origin city’s international passenger volume, flight time and early growth, it estimates the days to a first domestic import and splits the risk by port of entry — Incheon, Gimhae, Gimpo and others. It then continues on the domestic mobility network to arrival timing by region.',
        specs: [
          { label: 'First domestic import', value: 'D+days by origin (model scenario)' },
          { label: 'Ports of entry', value: 'Share by gateway — Incheon · Gimhae (Busan) · Gimpo and others' },
          { label: 'Domestic spread', value: 'Arrival timing by province (metapopulation model)' },
          { label: 'Global context', value: 'Spread twin over 159 countries · 1,671 air links · 314 land borders' },
        ],
      },
      {
        title: 'Domestic surveillance',
        kicker: 'DOMESTIC',
        tone: 'teal',
        items: [
          { title: 'Surges by notifiable disease', body: 'Reads the KDCA weekly notifications disease by disease, catching surges in individual diseases that a total would bury.', meta: 'kdca_anomaly' },
          { title: 'Domestic search signal', body: 'Tracks domestic interest in influenza, COVID-19, Ebola and more via Naver DataLab.', meta: 'naver_trends' },
          { title: 'Korean daily briefing', body: 'A Korean-language briefing on the domestic and global situation, generated every day.', meta: 'daily_brief' },
        ],
      },
      {
        title: 'Countermeasure production sovereignty (VALHALLA)',
        kicker: 'SOVEREIGNTY',
        tone: 'forest',
        body: 'From public sources it counts, threat by threat, whether a means of stopping it exists and whether that means can be made at home. A product with a single overseas supplier is a bottleneck: in a crisis the stockpile cannot be refilled.',
        points: [
          'Coverage by threat is computed from international emergency stockpiles and regulator-approved products.',
          'The WHO prequalification list gives the number of suppliers able to produce each product.',
          'ClinicalTrials.gov splits “still in development” down to trial phase.',
        ],
      },
      {
        title: 'National procurement watch',
        kicker: 'PROCUREMENT',
        tone: 'amber',
        body: 'Every day it tracks biosecurity- and outbreak-related purchasing in Korea’s public tender system (KONEPS). What the government is preparing shows up in tenders first.',
      },
      {
        title: 'Data sovereignty',
        kicker: 'DATA SOVEREIGNTY',
        tone: 'violet',
        body: 'The signal-extraction path is designed to switch, in one place, to a self-hosted model, so sensitive data need not leave for overseas APIs. Details are on the security and data governance page.',
      },
    ],
    cta: {
      title: 'How public bodies engage',
      body: 'The steps from initial review to scoping, pilot operation and joint scoring are set out.',
      label: 'See how to engage',
      href: 'pilot',
    },
  },

  security: {
    metaTitle: 'Security and data governance',
    metaDescription: 'AEGIRON’s access control, audit of high-risk programs, privacy principles, data-sovereignty path, secret management and operational integrity.',
    eyebrow: 'SECURITY & GOVERNANCE',
    title: 'Security and data governance',
    lead: 'Infectious-disease intelligence touches public safety. Who can change what, how sensitive functions are controlled and where data goes — described exactly as implemented in code.',
    blocks: [
      {
        title: 'Access control',
        kicker: 'ACCESS CONTROL',
        tone: 'indigo',
        specs: [
          { label: 'Total API', value: '123 endpoints' },
          { label: 'Authentication required', value: '37 — state-changing, costly and high-risk functions' },
          { label: 'Method', value: 'X-API-Key header · multiple labelled keys · constant-time comparison' },
          { label: 'With no key configured', value: 'All write APIs disabled — never left open' },
        ],
        note: 'Read APIs return processed public data and are public. Any call that changes data or incurs cost requires a key.',
      },
      {
        title: 'High-risk program control',
        kicker: 'HEIMDALL · VALHALLA',
        tone: 'violet',
        points: [
          'The highest-grade internal programs (HEIMDALL and others) require authentication, and every call is kept in an audit log by key label.',
          'HEIMDALL is **defensive detection only.** It has no sequence design, synthesis, optimisation or evasion function.',
          'External disclosure or redistribution of results requires approval, and the response says so.',
        ],
      },
      {
        title: 'Privacy principles',
        kicker: 'PRIVACY',
        tone: 'teal',
        points: [
          'What is collected is public material — health-authority reports, news coverage and public statistics. No individual patient data is handled.',
          'The website and dashboard run without login, advertising or visitor-tracking tools.',
        ],
      },
      {
        title: 'Data sovereignty',
        kicker: 'SOVEREIGNTY',
        tone: 'forest',
        body: 'The model layer that performs signal extraction is designed to change provider in one place, so it can move to a self-hosted (including on-premises) model. A national body can run it without sending sensitive data to external APIs.',
      },
      {
        title: 'Secret management and operational integrity',
        kicker: 'INTEGRITY',
        tone: 'sky',
        items: [
          { title: 'Secret management', body: 'API keys and credentials live only in production environment variables — never in the repository or documents.' },
          { title: 'Release gate', body: 'Only code that passes all 2,145 automated tests ships.' },
          { title: 'Silent-failure watch', body: 'Source health and quality invariants check the integrity of collection and computation every cycle.' },
          { title: 'Tamper evidence', body: 'Forecast records are sealed by hash and their time anchored to the Bitcoin blockchain.' },
        ],
      },
    ],
    cta: {
      title: 'Need material for a security review?',
      body: 'You can request descriptions of the architecture and controls for an institutional security review.',
      label: 'Contact us',
      href: 'contact',
    },
  },

  press: {
    metaTitle: 'Media kit',
    metaDescription: 'A one-line and one-paragraph description of AEGIRON, key facts, the introduction video and image-use guidance.',
    eyebrow: 'PRESS',
    title: 'Media kit',
    lead: 'Material you can use as-is when introducing AEGIRON in articles, talks or reports. Every figure is measured; there are no accuracy or lead-time claims.',
    blocks: [
      {
        title: 'One-liner',
        kicker: 'ONE-LINER',
        tone: 'teal',
        body: 'AEGIRON is a global infectious-disease early-warning system based in Busan, South Korea, that analyses local reporting from 178 countries in 52 languages and official surveillance data every hour to judge outbreak anomalies and compute spread and response scenarios.',
      },
      {
        title: 'Boilerplate',
        kicker: 'BOILERPLATE',
        tone: 'indigo',
        body: 'AEGIRON aims to catch the signal before an outbreak becomes international news. With 23 data sources and 114 algorithm modules it judges anomalies by country and, when an alert is raised, computes a 159-country spread simulation and intervention scenarios alongside it. Every forecast is sealed on the blockchain when made and scored automatically against later official declarations, and the system, methodology, data and limits are open from the start. Two R&D programs — defensive genomic screening (HEIMDALL) and countermeasure readiness (VALHALLA) — carry the national-biosecurity axis.',
      },
      {
        title: 'Key facts',
        kicker: 'FACT SHEET',
        tone: 'sky',
        specs: [
          { label: 'Headquarters', value: 'Busan, South Korea' },
          { label: 'Surveillance reach', value: '178 countries · 52 languages of local reporting' },
          { label: 'Data sources', value: '23 · collected hourly' },
          { label: 'Algorithm modules', value: '114' },
          { label: 'Public API', value: '123 endpoints' },
          { label: 'What is open', value: 'System · methodology · data sources · limits · forecast ledger' },
        ],
        note: 'Measured as of 2026-10-18. Please cite with the date.',
      },
      {
        title: 'Video and images',
        kicker: 'ASSETS',
        tone: 'forest',
        items: [
          { title: 'Introduction video', body: 'You may link the AEGIRON introduction video (YouTube) from the home page.', meta: 'youtu.be/2Uzl-5JgLjs' },
          { title: 'Operational screens', body: 'Dashboard captures on the live operations page may be used with credit to AEGIRON.', meta: '/live' },
          { title: 'Public photos', body: 'Field photos on this site are public-domain or freely licensed works of their authors. Please follow each photo’s source and licence.', meta: 'Credit shown per photo' },
        ],
      },
    ],
    cta: {
      title: 'Press and interview requests',
      body: 'Get in touch if you need more material or an interview.',
      label: 'Contact us',
      href: 'contact',
    },
  },

  pilot: {
    metaTitle: 'How to engage — from review to pilot',
    metaDescription: 'Engaging with AEGIRON runs in five steps: review of the open system, scoping, pilot operation, joint scoring and expansion.',
    eyebrow: 'HOW TO ENGAGE',
    title: 'How to engage',
    lead: 'You can review the whole system first without booking a demo. The pilot that follows is designed to start without any of your own data.',
    blocks: [
      {
        title: 'Five steps',
        kicker: 'PROCESS',
        tone: 'indigo',
        items: [
          { title: '01 · Initial review', body: 'Look at the open dashboard, methodology, data sources and forecast ledger first. The review needs no contract.', meta: 'On your own' },
          { title: '02 · Scoping', body: 'We agree together on countries and diseases of interest, alert channels (Telegram, email), deliverable formats and evaluation criteria.', meta: 'Joint design' },
          { title: '03 · Pilot operation', body: 'For an agreed period you receive tailored alerts, briefings and country risk reports and put them to work.', meta: 'Agreed period' },
          { title: '04 · Joint scoring', body: 'Alerts and forecasts from the pilot are scored together against official declarations, straight from the sealed record.', meta: 'Record that cannot be edited' },
          { title: '05 · Expansion', body: 'Scope, integration (API) and operating model widen based on the evaluation.', meta: 'Evaluation-led' },
        ],
      },
      {
        title: 'What you receive',
        kicker: 'DELIVERABLES',
        tone: 'teal',
        points: [
          'Tailored alerts — Critical and High alerts in your scope, delivered in real time',
          'Country risk reports — signal evidence, vulnerability and spread potential',
          'Intervention scenarios — no-response vs intervention per alert (labelled as model scenarios)',
          'Daily briefings and API access',
        ],
      },
      {
        title: 'What you need to bring',
        kicker: 'WHAT YOU NEED',
        tone: 'forest',
        points: [
          'Countries and diseases of interest, and the purpose',
          'A contact and an alert channel',
          'No customer data is required — it starts from public sources alone.',
        ],
        note: 'Duration and terms are agreed according to scope.',
      },
    ],
    cta: {
      title: 'Start with the review',
      body: 'After reviewing, get in touch with questions or a pilot proposal.',
      label: 'Contact us',
      href: 'contact',
    },
  },

  developers: {
    metaTitle: 'Developers · API',
    metaDescription: 'The AEGIRON REST API — 123 endpoints, JSON responses, X-API-Key authentication and OpenAPI docs. Guidance for integrating institutional systems.',
    eyebrow: 'DEVELOPERS',
    title: 'Developers · API',
    lead: 'Every value the dashboard shows comes from the same REST API. You can pull alerts, risk indices and briefings straight into an institutional system.',
    blocks: [
      {
        title: 'Basics',
        kicker: 'BASICS',
        tone: 'sky',
        specs: [
          { label: 'Base URL', value: 'https://epiweather-api-production.up.railway.app' },
          { label: 'Format', value: 'REST · JSON' },
          { label: 'Authentication', value: 'Reads public · writes/high-risk via X-API-Key' },
          { label: 'Interactive docs', value: '/docs (OpenAPI)' },
        ],
      },
      {
        title: 'Frequently used endpoints',
        kicker: 'QUICK START',
        tone: 'teal',
        items: [
          { title: 'Country risk ranking', body: 'Full ranking of final risk by country (raw risk × vulnerability).', meta: 'GET /api/risk-index' },
          { title: 'Alerts', body: 'Current alert candidates after grading and daily caps.', meta: 'GET /api/alerts' },
          { title: 'Daily briefing', body: 'The daily situation briefing by language.', meta: 'GET /api/daily-brief?lang=en' },
          { title: 'Forecast ledger', body: 'Sealed forecasts and the scorecard.', meta: 'GET /api/predictions · /scorecard' },
          { title: 'Timestamp proof', body: 'Blockchain timestamp-proof status per forecast.', meta: 'GET /api/predictions/{id}/timestamp-proof' },
          { title: 'Operational status', body: 'Source health, data volume and scheduler state.', meta: 'GET /api/status' },
        ],
      },
    ],
    cta: {
      title: 'Need an integration key?',
      body: 'We issue per-institution API keys for write and high-risk integrations.',
      label: 'Contact us',
      href: 'contact',
    },
  },

  diseases: {
    metaTitle: 'Disease watch',
    metaDescription: 'Key infections AEGIRON watches — avian influenza H5N1, Ebola, Marburg, mpox, cholera, measles, MERS and Nipah: what it watches for each, and the parameters its simulations use.',
    eyebrow: 'DISEASES',
    title: 'Disease watch',
    lead: 'Even within one alert system, the signal that moves first differs by disease. For the key infections, here is what AEGIRON watches and which literature parameters its spread simulation uses.',
    blocks: [],
    cta: {
      title: 'See each disease’s signals now',
      body: 'The latest signals by disease are on the dashboard and in the daily briefings.',
      label: 'Open the live dashboard',
      href: '/dashboard',
    },
  },
};
