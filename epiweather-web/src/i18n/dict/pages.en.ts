import type { PagesDict } from '../types';

/**
 * English subpage content.
 *
 * ★ Figures here are measured values ★
 * 23 operational collection sources · 116 algorithm modules (114 engines + YGGDRASIL · BAIKAL) · 126 endpoints · 2,201 automated tests (measured 2026-10-19).
 *
 * ★ HARD RULE ★ No accuracy or lead-time claims.
 */
export const pagesEn: PagesDict = {
  platform: {
    metaTitle: 'Platform — the whole world as one watch',
    metaDescription:
      'AEGIRON collects local reporting from 178 countries in 52 languages, together with official surveillance data, and processes it in five stages — collect, extract, judge, forecast, respond.',
    eyebrow: 'PLATFORM',
    title: 'The whole world as one watch',
    lead: 'Disease does not wait at borders. AEGIRON binds local reporting from 178 countries, each nation’s official data, and environmental, trade and genomic signals into one system, and computes every hour where something differs from normal. Here are the five stages a signal passes through to become an alert and a response scenario.',
    blocks: [
      {
        title: 'Platform at a glance',
        kicker: 'AT A GLANCE',
        tone: 'teal',
        specs: [
          { label: 'Surveillance reach', value: '178 countries · 52 languages of local reporting (179 feeds)' },
          { label: 'Live sources', value: '23 · collected automatically every hour' },
          { label: 'Spread model', value: '159 countries · 1,671 air links · 314 land borders' },
          { label: 'Algorithm modules', value: '116 (114 engines · YGGDRASIL ontology · BAIKAL MOB state layer)' },
          { label: 'Public API', value: '126 endpoints' },
          { label: 'Quality control', value: '2,201 automated tests — all must pass before anything ships' },
        ],
        note: 'Measured against the repository and operational logs on 2026-10-19.',
      },
      {
        title: '01 · Collect',
        kicker: 'STAGE 01',
        tone: 'teal',
        body: 'Signals arrive every hour from 23 operational sources. Material as different as official reports from international bodies and local-language reporting from 178 countries is normalised into one signal format, and each source carries its own reliability weight through every later calculation.',
        items: [
          { title: 'Official reporting', body: 'WHO regional offices for Africa and the Americas, the Korea Disease Control and Prevention Agency, Japan’s infectious-disease weekly report, Hong Kong’s Centre for Health Protection and Brazil’s InfoDengue. We respect each body’s own severity grade.' },
          { title: 'Local-language reporting', body: 'The first local coverage before the international press translates it — held to the same standard even in regions with large surveillance gaps.' },
          { title: 'Environmental and leading signals', body: 'Wastewater surveillance (US CDC NWSS), a disaster watch window (GDACS), polar observation and medical-supply trade statistics catch shifts in outbreak conditions and preparedness behaviour first.' },
        ],
      },
      {
        title: '02 · Extract',
        kicker: 'STAGE 02',
        tone: 'sky',
        body: 'Disease, country, cases and deaths are structured from PDF tables and article text. The rule is clear — only confirmed values become numbers.',
        points: [
          'Only columns whose meaning is confirmed by the table header are used. Nothing is guessed by position, so numbers do not drift silently.',
          '“New in the last seven days” and “cumulative”, “suspected” and “confirmed”, are kept as separate fields.',
          'A “total” row is not a country and is excluded, keeping trend analysis clean.',
          'Extracted numbers are cross-checked against the source text, and the source location is recorded.',
        ],
      },
      {
        title: '03 · Judge',
        kicker: 'STAGE 03',
        tone: 'crimson',
        body: 'Anomalies are computed **against the usual level of that country and that indicator,** not in absolute terms. The same five cases mean something different in a country that reports constantly and in one that is usually quiet.',
        points: [
          'Anomaly scores come from deviation against a country- and indicator-specific baseline and the US CDC EARS standard.',
          'Older signals contribute less over time (half-life decay).',
          '“Measured and found normal” is reported separately from “no data to judge”.',
          'Alerts carry a daily cap by grade, so only what truly needs attention rises to the top.',
        ],
      },
      {
        title: '04 · Forecast',
        kicker: 'STAGE 04',
        tone: 'indigo',
        body: 'Transmission models estimate the scale of spread and cross-border import routes, simulating with disease-specific parameters on an air-and-land network that links 159 countries.',
        points: [
          'Models are fitted with disease-specific R0 and fatality rates measured in the literature.',
          'Contact-transmission pathogens get a **reachable population** of their own, for a realistic scale.',
          'Modelled death estimates are checked automatically against the largest outbreaks on record, and a warning travels with any value outside that range.',
        ],
      },
      {
        title: '05 · Respond',
        kicker: 'STAGE 05',
        tone: 'forest',
        body: 'We do not stop at “what is coming”. No-response and intervention scenarios are compared to show which measures, at what intensity, break transmission.',
        items: [
          { title: 'No-response baseline', body: 'The path with no measures taken is kept as the baseline.' },
          { title: 'Comparing interventions', body: 'Combinations of isolation, distancing, vaccination and treatment are tested to find where the effective reproduction number falls below 1.' },
          { title: 'Forecast sealing', body: 'Forecasts and scenarios are sealed with a hash at the moment they are produced, so a third party can verify what we foresaw and when.' },
        ],
      },
    ],
    cta: {
      title: 'See the five stages running for yourself',
      body: 'On the live dashboard you can watch the whole chain — from collection to response — run in real time, with no login.',
      label: 'Open the live dashboard',
      href: '/dashboard',
    },
  },

  techSpec1: {
    metaTitle: 'Technology I — surveillance and collection',
    metaDescription:
      'Local-language news surveillance across 178 countries and 52 languages, automated PDF extraction of official reports, environmental/trade/procurement leading indicators, the six-layer anomaly index, reporting-silence watch, two-stage detection, and source-health monitoring — the spec and engines of AEGIRON’s surveillance layer.',
    eyebrow: 'TECHNOLOGY · I',
    title: 'Surveillance and collection',
    lead: 'AEGIRON’s first layer is a watch that sweeps the whole planet every hour. It runs by itself, finding what “differs from normal” across local-language reporting, official bulletins, environmental signals, trade and procurement records. The spec first, then each engine.',
    photo: {
      src: '/media/photos/iss-city-lights.jpg',
      alt: 'City lights at night seen from the International Space Station',
      caption: 'Türkiye at night, seen from the International Space Station. The networks that move people and goods are the same routes an outbreak travels.',
      credit: 'NASA JSC · Public domain',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:The_city_lights_of_T%C3%BCrkiye_sparkle_below_the_International_Space_Station_(iss074e0225549).jpg',
    },
    blocks: [
      {
        title: 'Surveillance layer — spec sheet',
        kicker: 'SPEC SHEET',
        tone: 'teal',
        specs: [
          { label: 'Local-language reporting', value: '178 countries · 52 languages · 179 feeds · hourly' },
          { label: 'Report classification', value: 'LLM headline classifier (real outbreak reports only) + keyword fallback' },
          { label: 'Official reporting', value: 'WHO regional offices · 6 national health authorities · WHO IRIS' },
          { label: 'Document extraction', value: 'PDF table structuring (NVIDIA document model) → normalised signal → trend' },
          { label: 'Anomaly index', value: 'Six-layer weighted sum (official · unofficial · behavioural · environmental · animal · unexplained)' },
          { label: 'Standard detection', value: 'US CDC EARS C1 · C2 · C3 + country-level z-score baseline' },
          { label: 'Detection design', value: 'Sentinel (fast) → verification layer (cross-check), two stages' },
          { label: 'Operational reliability', value: 'Source health · quality invariants · capability ledger — self-checked every cycle' },
        ],
      },
      {
        title: 'Local-language news surveillance',
        kicker: 'ENGINE · local_news',
        tone: 'teal',
        body: 'Before the international press translates it, the first signal is often a report in the local language. We take 178 countries as news aggregated by country and language, measure the density of disease vocabulary, and have a language model read the headlines to select only reports of a real outbreak or cluster. We do not curate low-risk countries out — a pandemic can begin anywhere.',
        points: [
          'The unit of detection is the intersection of country, language and disease — one country through a single aggregation window.',
          'Regions commercial surveillance services rarely cover — Africa, Central Asia, Pacific island states — are watched to the same standard.',
          'When several feeds report the same event, cross-language clustering groups them into one.',
          'If the primary source is blocked, it switches automatically to a fallback headline provider so surveillance never stops.',
        ],
      },
      {
        title: 'Automated extraction of official reports',
        kicker: 'ENGINE · who_iris → pdf_table_extract → bulletin_*',
        tone: 'sky',
        body: 'In many documents — the WHO Africa weekly situation report, for one — the key figures by country and disease live only inside PDF tables. AEGIRON fetches the reports from the WHO document repository, restores the tables with a document model, converts them into normalised signals, loads them, and stitches successive editions into a trend.',
        items: [
          { title: 'Fetch', body: 'Pulls weekly reports reliably from WHO IRIS. Editions already loaded are not fetched again.', meta: 'who_iris · bulletin_collect' },
          { title: 'Table restore', body: 'Restores PDF tables to row-and-column structure with the NVIDIA document model.', meta: 'pdf_table_extract' },
          { title: 'Signalise · load', body: 'Separates “7-day new”, “cumulative”, “suspected” and “confirmed” and loads them in the form the alert engine reads.', meta: 'bulletin_signals · bulletin_ingest' },
          { title: 'Trend', body: 'Turns per-edition point signals into a time series to see speed and direction.', meta: 'bulletin_trend' },
        ],
      },
      {
        title: 'Environmental · trade · procurement leading indicators',
        kicker: 'ENGINE · disaster_watch · polar_* · comtrade_signals · procurement_watch',
        tone: 'forest',
        body: 'Outbreaks leave traces outside the health system first. Disasters, climate, polar change, medical-supply imports and government procurement notices are not the outbreak itself but signals of outbreak conditions and preparedness behaviour. AEGIRON watches them as a separate layer.',
        items: [
          { title: 'Disaster watch window', body: 'After floods, quakes and storms, the country is watched at a lower threshold through the window when water- and vector-borne risk rises.', meta: 'disaster_watch · GDACS' },
          { title: 'Polar · glacier', body: 'Change in permafrost and 27 glacier mountain regions, observed with baseline and trend.', meta: 'polar_signals · polar_baseline · polar_trend · glacier_regions' },
          { title: 'Climate · forest', body: 'Temperature and rainfall anomalies and forest loss/fire read as spillover-condition indicators.', meta: 'climate_signals · forest_signals · deforestation_signals' },
          { title: 'Medical-supply trade', body: 'UN Comtrade detects import surges of masks, PPE and test kits by country.', meta: 'comtrade_signals' },
          { title: 'Government procurement', body: 'Tracks biosecurity-related buying moves in Korea’s public tender system.', meta: 'procurement_watch' },
          { title: 'Wastewater · animal', body: 'Pathogen concentration in US wastewater plants and WOAH animal-outbreak reports.', meta: 'CDC NWSS · wahis' },
        ],
      },
      {
        title: 'Six-layer anomaly index and standard detection',
        kicker: 'ENGINE · gai · ears · anomaly_engine · kdca_anomaly',
        tone: 'crimson',
        body: 'Signals from six layers — official, unofficial, behavioural, environmental, animal and unexplained — are each converted into an anomaly score against their usual level, weighted by source reliability, and combined into one index (GAI). On top sits the surveillance-epidemiology standard, the US CDC’s EARS C1/C2/C3, which stays stable even where the baseline is short.',
        points: [
          'Each signal is scored as a z-score against its own historical distribution, with the latest value excluded from the baseline.',
          'Each layer carries a different reliability weight — official data and social posts cannot weigh the same.',
          'EARS uses a guard band so early outbreak values do not contaminate the baseline.',
          'Korea’s notifiable diseases are watched per disease, so an individual disease’s move is not lost in the total.',
        ],
      },
      {
        title: 'Reporting silence · unexplained · high-risk pathogens',
        kicker: 'ENGINE · negative_space · unexplained · pathogen_sentinel',
        tone: 'violet',
        body: 'Danger does not come only when numbers rise. AEGIRON watches three types that counting alone misses, each with a dedicated engine.',
        items: [
          { title: 'Reporting-silence watch', body: 'When a normally active channel falls below half its baseline, that is a signal. It targets cases, like 2014 Guinea Ebola, where the reporting system collapses before the spread.', meta: 'negative_space' },
          { title: 'Unexplained clusters', body: 'Counts clusters that match no known disease pattern. The December 2019 pneumonia of unknown cause in Wuhan is the type.', meta: 'unexplained' },
          { title: 'High-risk single reports', body: 'For pathogens like plague, anthrax and smallpox — where one event is already news — it raises a single report without waiting for counts to build.', meta: 'pathogen_sentinel' },
        ],
      },
      {
        title: 'Two-stage detection and operational reliability',
        kicker: 'ENGINE · sentinel · verification · source_health · quality_health',
        tone: 'sky',
        body: 'Fast detection and accurate confirmation are different engines. The sentinel queues anything moving past twice its baseline at once; the verification layer cross-checks with real-time search whether it is a real event. And a separate layer watches, every cycle, whether the whole thing is healthy.',
        items: [
          { title: 'Sentinel', body: 'A fast detection layer with a low threshold, set to miss nothing.', meta: 'sentinel' },
          { title: 'Verification layer', body: 'Confirms what the sentinel raises with real-time web search and records confirm/dismiss.', meta: 'verification' },
          { title: 'Source health', body: 'Counts whether a value actually arrived, not whether collection merely ran.', meta: 'source_health' },
          { title: 'Quality invariants', body: 'Catches the cases where the source lives but the computation has broken.', meta: 'quality_health · capability_ledger' },
        ],
      },
    ],
    cta: {
      title: 'The analysis and response layer is in Technology II',
      body: 'Country risk index, 7/14-day forecasts, a 159-country spread simulation, per-alert intervention scenarios, genomic screening and forecast self-verification follow.',
      label: 'See Technology II',
      href: 'technology-advanced',
    },
  },

  techSpec2: {
    metaTitle: 'Technology II — analysis and response',
    metaDescription:
      'Country risk index, alert-fatigue control, 7/14-day forecasts, a nowcast learning framework, a 159-country spread digital twin, import-date estimation, per-alert intervention scenarios, genomic screening, and forecast scoring/sealing — the spec and engines of AEGIRON’s analysis and response layer.',
    eyebrow: 'TECHNOLOGY · II',
    title: 'Analysis and response',
    lead: 'If the surveillance layer finds what differs, this layer answers where, how much, and what to do. It quantifies risk by country, simulates spread, compares intervention effects, and scores every one of its own forecasts.',
    photo: {
      src: '/media/photos/avian-influenza-h5n1.jpg',
      alt: 'Colorized transmission electron micrograph of avian influenza A(H5N1) virus particles',
      caption: 'Avian influenza A(H5N1) virus particles, colorized transmission electron micrograph. Public material from the US CDC.',
      credit: 'CDC / Cynthia Goldsmith · Public domain',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:Colorized_transmission_electron_micrograph_of_Avian_influenza_A_H5N1_viruses.jpg',
    },
    blocks: [
      {
        title: 'Analysis & response layer — spec sheet',
        kicker: 'SPEC SHEET',
        tone: 'indigo',
        specs: [
          { label: 'Country risk index', value: 'Raw risk × national vulnerability (health infra · density · airport connectivity · border movement)' },
          { label: 'Alert system', value: 'Critical 90+ (3/day) · High 80+ (5/day) · Medium 70+ · Telegram real-time push' },
          { label: 'Trend forecast', value: '7-day · 14-day — linear-regression / exponential-smoothing ensemble' },
          { label: 'Spread digital twin', value: 'Metapopulation SEIR · 159 countries · 1,671 air links · 314 land borders' },
          { label: 'Disease parameters', value: 'Literature-measured R0 · fatality rate for 14 diseases' },
          { label: 'Genomic screening', value: 'Composition statistics · Evo2 order naturalness · ColabFold homology coverage' },
          { label: 'Self-verification', value: 'Automatic scoring (hit · Brier · calibration) · lead-time ledger · Bitcoin-chain sealing' },
        ],
      },
      {
        title: 'Country risk index and alert-fatigue control',
        kicker: 'ENGINE · country_risk · alerts · notifier',
        tone: 'crimson',
        body: 'A country’s final risk is the raw risk from signals multiplied by that nation’s vulnerability — the same signal becomes a greater risk in a country with weak health infrastructure and many international links. Alerts are filtered by grade and a daily cap, so recipients get only what truly needs attention, immediately.',
        points: [
          'Official figures (Korea, Brazil, Japan, Hong Kong) and extracted-report values are combined, weighted by source reliability.',
          'The vulnerability index is filled with measured values from public indicators such as the World Bank.',
          'Critical and High alerts are pushed over Telegram at once, and candidates over the cap are kept on the record rather than discarded.',
        ],
      },
      {
        title: 'Forecasting and the nowcast learning framework',
        kicker: 'ENGINE · forecast_engine · nowcast_*',
        tone: 'indigo',
        body: 'Indicator time series are extrapolated 7 and 14 days ahead for the daily briefing. Separately, a nowcast framework learns “which signal led to a real outbreak”. It assembles a training set from past official declarations and the reporting volume at that time, evaluates performance only on future windows not used in training, and lets you choose the balance of recall and false-alarm rate.',
        items: [
          { title: 'Auto-assembled training set', body: 'Builds up labels (official declarations) and features (reporting volume at that time) daily.', meta: 'nowcast_dataset · nowcast_backfill' },
          { title: 'Prospective evaluation', body: 'Scores on a future it could not have known, not on the training data.', meta: 'nowcast_eval' },
          { title: 'Operating-point choice', body: 'Picks the point between recall and false-alarm rate that the organisation wants.', meta: 'nowcast_threshold' },
        ],
      },
      {
        title: 'Spread digital twin and import estimation',
        kicker: 'ENGINE · digital_twin · country_borders · global_inflow',
        tone: 'indigo',
        body: 'A metapopulation SEIR model with 159 countries as nodes, and 1,671 air-linked country pairs and 314 land borders as edges. Given an origin and a disease, it simulates arrival time and scale by country, and reports countries no route reaches separately from countries for which there is no data.',
        items: [
          { title: 'Cross-border spread', body: 'Reflects air passengers and land movement together to order countries by arrival.', meta: 'digital_twin · country_borders' },
          { title: 'Domestic import date', body: 'From the origin city’s international passenger volume, flight time and early growth, it estimates days to a first import and per-gateway risk.', meta: 'global_inflow · origin_catalog' },
          { title: 'Sub-national resolution', body: 'Brings country-level risk down to administrative units.', meta: 'geo_resolution' },
        ],
      },
      {
        title: 'Per-alert intervention scenarios',
        kicker: 'ENGINE · alert_intervention · defense · disease_params · decision_tree',
        tone: 'forest',
        body: 'For every new critical or high alert, an SEIR defence simulation runs with disease-specific parameters and attaches the difference between no response and intervention — in deaths and days of hospital overload. An alert no longer ends at “what is coming” but answers “which measure changes what”.',
        points: [
          'It varies the start and intensity of isolation, distancing and vaccination to find the combination that pushes the effective reproduction number below 1.',
          'Literature-measured R0 and fatality rates for 14 diseases calibrate the model, and results are labelled “model scenario”.',
          'A rule-based decision tree generates response recommendations by risk level instantly.',
        ],
      },
      {
        title: 'Genomic screening (HEIMDALL)',
        kicker: 'ENGINE · genome_signals · evo2_naturalness · msa_homology',
        tone: 'violet',
        body: 'It reads a sequence from three different angles. Composition statistics look at base make-up, Evo2 at the naturalness of order, and homology search at whether natural proteins explain the whole sequence. It is defensive detection only, and its result is a review priority, not a verdict.',
        points: [
          'Composition statistics (CAI, CpG) target an unnatural make-up; Evo2 order naturalness targets spliced or recombined stretches.',
          'Homology search is a public-database lookup, not a trained model, so it works even on pathogens Evo2 cannot handle.',
          'Evo2 excluded eukaryotic-host viruses from training, so the applicable domain is declared; outside it the score is reported but no flag is raised.',
        ],
        note: 'The detailed spec and per-taxon basis are set out under the HEIMDALL special program.',
      },
      {
        title: 'Self-verification — scoring and sealing',
        kicker: 'ENGINE · prediction_resolver · lead_time_ledger · prediction_timestamp',
        tone: 'teal',
        body: 'To prove forecasts as a record, we put the verification in the code. Recorded forecasts are scored daily against the official declarations that follow, the moment a signal was first seen is fixed before any declaration, and every forecast is sealed at the moment it is made.',
        items: [
          { title: 'Automatic forecast scoring', body: 'Unresolved forecasts are checked daily against official declarations and sorted into hit, miss or undetermined. View spikes and case-count updates are not used as ground truth, so we do not score our signals with our own signals.', meta: 'prediction_resolver · prediction_scoring' },
          { title: 'Lead-time ledger', body: 'Records the moment a signal was first seen before any official declaration. A lead time found by searching backwards after a declaration is not accepted as a measurement.', meta: 'lead_time_ledger' },
          { title: 'Forecast sealing', body: 'The SHA-256 hash of a forecast record is anchored to the Bitcoin chain via OpenTimestamps. A third party can verify for themselves that it was not rewritten later.', meta: 'prediction_timestamp' },
        ],
      },
    ],
    cta: {
      title: 'Two layers, one chain',
      body: 'Detect → judge → forecast → simulate → prescribe → self-verify → seal. The screen where that chain actually runs is the live dashboard.',
      label: 'Live dashboard',
      href: '/dashboard',
    },
  },

  engines: {
    metaTitle: 'Engine catalogue — the full map of 114 modules',
    metaDescription:
      'All 114 of AEGIRON’s algorithm modules, grouped into seven: surveillance, extraction, judgement, forecast, genomics, countermeasures and verification. What each module does, and whether it runs hourly or on request.',
    eyebrow: 'ENGINE CATALOGUE',
    title: '114 modules, seven systems',
    lead: 'AEGIRON is not one large model but 114 modules, each doing one thing well, meshed together — because watching the whole world takes that many angles. The core modules are organised into seven named systems — HUGINN, MIMIR, FORSETI, SKULD, HEIMDALL, VALHALLA and VAR — the engine layer of AEGIRON’s flagship system (see BAIKAL MOB).',
    blocks: [
      {
        title: 'HUGINN — Surveillance — gather signals, find anomalies',
        kicker: 'SYSTEM 01 · HUGINN',
        tone: 'teal',
        items: [
          { title: 'Local-language news watch', body: 'Selects outbreak reports from news aggregated across 178 countries and 52 languages.', meta: 'local_news · hourly' },
          { title: 'Six-layer anomaly index', body: 'Combines six layers of signals, scored against their usual level, into one index.', meta: 'gai · hourly' },
          { title: 'Reporting-silence watch', body: 'Treats an active channel falling quiet as a signal.', meta: 'negative_space · hourly' },
          { title: 'Unexplained clusters', body: 'Counts clusters not explained by any known disease.', meta: 'unexplained · hourly' },
          { title: 'High-risk single report', body: 'Raises pathogens where one event is news — plague, anthrax — on a single report.', meta: 'pathogen_sentinel · hourly' },
          { title: 'Standard detection', body: 'Catches anomalies with US CDC EARS C1/C2/C3 and a z-score baseline.', meta: 'ears · anomaly_engine · kdca_anomaly' },
          { title: 'Two-stage detection', body: 'A fast sentinel raises; a verification layer cross-checks.', meta: 'sentinel · verification' },
          { title: 'Disaster · polar · climate', body: 'Reads environmental signals of changing outbreak conditions as leading indicators.', meta: 'disaster_watch · polar_* · climate_signals' },
          { title: 'Trade · procurement · animal', body: 'Tracks medical-supply imports, government procurement and animal outbreaks.', meta: 'comtrade_signals · procurement_watch · wahis' },
        ],
      },
      {
        title: 'MIMIR — Extraction — turn text and tables into numbers',
        kicker: 'SYSTEM 02 · MIMIR',
        tone: 'sky',
        items: [
          { title: 'PDF table extraction', body: 'Restores tables in health reports to row-and-column structure.', meta: 'pdf_table_extract' },
          { title: 'Report signalise · load', body: 'Converts restored tables into normalised signals, loads them and derives trends.', meta: 'bulletin_signals · bulletin_ingest · bulletin_trend' },
          { title: 'NLP signal extraction', body: 'Turns free-text reporting into structured JSON so it can be aggregated.', meta: 'nlp_extract' },
          { title: 'Country resolution', body: 'Resolves free-text locations into lists of ISO country codes.', meta: 'country_resolve · geo_resolution' },
          { title: 'Event deduplication', body: 'Groups the same event from several sources into one to prevent duplicate alerts.', meta: 'event_dedup' },
          { title: 'Extraction model layer', body: 'Lets the extraction path be switched in one place toward a proprietary model.', meta: 'aegiron_model · nvidia' },
        ],
      },
      {
        title: 'FORSETI — Judgement — decide whether to raise an alert',
        kicker: 'SYSTEM 03 · FORSETI',
        tone: 'crimson',
        items: [
          { title: 'Country risk index', body: 'Multiplies raw risk by national vulnerability for a final risk.', meta: 'country_risk · country_indicators' },
          { title: 'Alert-fatigue control', body: 'Keeps only the alerts that truly need attention, by grade and daily cap.', meta: 'alerts' },
          { title: 'Real-time notification', body: 'Pushes Critical and High alerts over Telegram at once.', meta: 'notifier' },
          { title: 'Reliability engine', body: 'Weighs rumour and estimate differently from official primary data.', meta: 'trust' },
          { title: 'Risk quantification', body: 'Produces relative indicators insurance and finance can compare.', meta: 'risk_quantification' },
        ],
      },
      {
        title: 'SKULD — Forecast · simulation — see where it will spread',
        kicker: 'SYSTEM 04 · SKULD',
        tone: 'indigo',
        items: [
          { title: '7/14-day forecast', body: 'Extrapolates indicator time series with an ensemble.', meta: 'forecast_engine' },
          { title: 'Spread digital twin', body: 'SEIR simulation over a 159-country air-and-land network.', meta: 'digital_twin · country_borders' },
          { title: 'Domestic import date', body: 'Estimates days to a first domestic import from the origin.', meta: 'global_inflow · origin_catalog' },
          { title: 'Nowcast learning', body: 'Assembles signal→outbreak training sets and evaluates prospectively.', meta: 'nowcast_dataset · nowcast_eval' },
          { title: 'Knowledge graph', body: 'Interprets signals through cause-and-effect chains.', meta: 'knowledge_graph' },
        ],
      },
      {
        title: 'HEIMDALL — Genomics — read sequences defensively',
        kicker: 'SYSTEM 05 · HEIMDALL',
        tone: 'violet',
        items: [
          { title: 'Composition statistics', body: 'Looks at unnatural make-up with CAI, CpG and similar.', meta: 'genome_signals' },
          { title: 'Order naturalness', body: 'Measures the naturalness of sequence order with Evo2.', meta: 'evo2_naturalness' },
          { title: 'Homology chimera detection', body: 'Searches whether natural proteins cover the whole sequence.', meta: 'msa_homology' },
          { title: 'Lineage tracking', body: 'Reads dominant-lineage change from Nextstrain re-analysis.', meta: 'genomic_variants' },
        ],
      },
      {
        title: 'VALHALLA — Countermeasures — count what can stop it (VALHALLA)',
        kicker: 'SYSTEM 06 · VALHALLA',
        tone: 'forest',
        items: [
          { title: 'Coverage gap', body: 'Which threats the current stockpile and approved products cannot cover.', meta: 'countermeasure_stockpile · approved_products' },
          { title: 'Production sovereignty', body: '“How many places can make it”, from the WHO list.', meta: 'vaccine_supply · countermeasure_pipeline' },
          { title: 'Readiness scopes', body: 'Answers preparedness by scope — domestic stockpile vs world supply.', meta: 'readiness_scopes · ihr_capacity' },
          { title: 'Intervention scenarios', body: 'Simulates the difference between no response and intervention per alert.', meta: 'alert_intervention · defense' },
          { title: 'Valhalla watch', body: 'Accumulates countermeasure readiness daily to see the trend.', meta: 'valhalla_watch' },
        ],
      },
      {
        title: 'VAR — Verification — we check our own numbers',
        kicker: 'SYSTEM 07 · VAR',
        tone: 'teal',
        items: [
          { title: 'Automatic forecast scoring', body: 'Sorts forecasts against official declarations into hit, miss or hold.', meta: 'prediction_resolver · prediction_scoring' },
          { title: 'Lead-time ledger', body: 'Fixes the moment a signal was first seen before any declaration.', meta: 'lead_time_ledger' },
          { title: 'Forecast sealing', body: 'Anchors a forecast hash to the Bitcoin chain.', meta: 'prediction_timestamp' },
          { title: 'Source health', body: 'Counts every cycle whether a value actually arrived.', meta: 'source_health' },
          { title: 'Quality invariants', body: 'Catches a broken computation even when the source lives.', meta: 'quality_health · capability_ledger' },
          { title: 'Launch readiness', body: 'Answers “are we ready to launch” as a measurement, not an opinion.', meta: 'launch_readiness' },
        ],
      },
    ],
    cta: {
      title: 'See the values these engines actually produce',
      body: 'The dashboard shows the signals and indicators these modules are generating right now.',
      label: 'Open the live dashboard',
      href: '/dashboard',
    },
  },

  programs: {
    metaTitle: 'Special programs — HEIMDALL · VALHALLA',
    metaDescription:
      'AEGIRON’s two internal R&D programs. HEIMDALL handles defensive genomic screening; VALHALLA, countermeasure readiness. Both run inside a stated honesty boundary, without overstating what they can do.',
    eyebrow: 'SPECIAL PROGRAMS',
    title: 'HEIMDALL · VALHALLA',
    lead: 'Most of the surveillance layers run in the open. But two axes are different in kind — genomic screening of biological threats, and national countermeasure readiness. Because they are sensitive, we handle ownership and access separately; this page states only what they do and do not do, without overstating any of it.',
    photo: {
      src: '/media/photos/ebola-virion.jpg',
      alt: 'Colorized transmission electron micrograph of an Ebola virus particle',
      caption: 'Ebola virus particle, colorized transmission electron micrograph. Public material from the US CDC — not AEGIRON laboratory data.',
      credit: 'CDC / Cynthia Goldsmith · Public domain',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:Ebola_virus_virion.jpg',
    },
    blocks: [
      {
        title: 'HEIMDALL — defensive genomic screening',
        kicker: 'PROGRAM · HEIMDALL',
        tone: 'violet',
        deep: true,
        body: 'Named for the watchman who guards the bridge in Norse myth. It is the defensive function of biosecurity screening — detecting and flagging whether a given genomic sequence shows signals that depart from the statistics of natural evolution. It looks at composition statistics, order naturalness and homology coverage together (the genomics layer of Technology II).',
        points: [
          '**Defensive detection only.** It does not design, synthesise or optimise sequences, nor provide any way to evade screening.',
          'The result is a “priority for close review”, not a verdict. A final judgement needs an expert and wet-lab work (is_screening_only).',
          'Bacteria, archaea, eukaryotic genomes and phages are in the applicable domain. Eukaryotic-host viruses fall outside it by a model limit, and that fact is stated in the response.',
        ],
        note: 'The endpoint requires authentication and every access is kept in an audit log. Raising the security grade does not raise the claims — classified means access control, not treating the unvalidated as validated.',
      },
      {
        title: 'VALHALLA — countermeasure readiness',
        kicker: 'PROGRAM · VALHALLA',
        tone: 'forest',
        deep: true,
        body: 'Rather than imitating molecular-level neutralisation prediction, it answers the questions one can actually defend — which threats our stockpile cannot cover (the coverage gap), and of those it does cover, which cannot be produced domestically (the production-sovereignty gap). These are the core questions of national biosecurity planning, and all of it is computed from public data.',
        items: [
          { title: 'Coverage gap', body: 'Which diseases have an international emergency stockpile or a regulatory-approved product. We do not touch non-public information such as national stockpile quantities.', meta: 'Public sources: WHO ICG, openFDA, etc.' },
          { title: 'Production sovereignty', body: 'From the WHO prequalification list, how many places in the world can make a given product. Of 56 products, 17 have a single supplier — a bottleneck this surfaces.', meta: 'A single point of supply = the risk a stockpile cannot be refilled' },
          { title: 'Development stage', body: 'Via ClinicalTrials.gov it splits “still in development” down to trial phase, separating the different states lumped into “no stockpile” (Phase 3 under way vs no phase listed).', meta: 'The distinction that sets preparedness priority' },
        ],
      },
      {
        title: 'The honesty boundary',
        accent: true,
        body: 'Both programs take not overstating capability as an operating rule. The boundary is fixed in the code comments, and the response carries it along.',
        points: [
          'HEIMDALL is still a **screening priority, not a verdict.**',
          'VALHALLA’s efficacy is an **aggregate of each countermeasure’s declared (label) efficacy**, not a molecular neutralisation prediction.',
          'Where data is missing, it does not invent it and conservatively leaves coverage “unknown”.',
        ],
        note: 'The program code names and organisational structure are AEGIRON’s own internal definitions, not an affiliation with a government body or an official security classification.',
      },
    ],
    cta: {
      title: 'The measured basis for the deep engines',
      body: 'The per-taxon measurements of the genomics layer and the network limits of the simulation are set out in Technology II.',
      label: 'See Technology II',
      href: 'technology-advanced',
    },
  },


  transparency: {
    metaTitle: 'Validation and limits — how the system verifies itself',
    metaDescription:
      'How AEGIRON built verification into the system, together with its known limits and data gaps — the mechanisms that keep a number from travelling further than its evidence.',
    eyebrow: 'VALIDATION & LIMITS',
    title: 'Validation and limits',
    lead: 'The most dangerous thing in disease surveillance is not a wrong forecast but one that cannot be checked. So AEGIRON built verification into the code. Here is how the system checks its own numbers, alongside its known limits.',
    blocks: [
      {
        title: 'Verification the system performs itself',
        kicker: 'SELF-CHECK',
        tone: 'teal',
        body: 'If limits are written only in documents, the numbers break away and are reused as-is on screens and in reports. So the verification is built into the code.',
        points: [
          '**Historical comparison** — modelled death estimates are compared automatically with the largest outbreak on record for that disease; well beyond that range, a “do not use in external material” warning is attached to the response.',
          '**Separating causes of failure** — when an outbreak is missed, “the model missed it” is reported separately from “there was no data to see it”. Mixing them inverts the diagnosis.',
          '**Prospective evaluation** — performance is scored only on a future that was unknowable at the time, never on training data.',
          '**Provenance** — when a disease name or country comes from context rather than a table, where it came from is recorded alongside it.',
        ],
      },
      {
        title: 'How forecasts are proven as a record',
        kicker: 'PROOF',
        tone: 'indigo',
        body: 'The claim to “know before others” means something only when there is a path to prove it. AEGIRON seals every forecast at the moment it is made and scores it daily against the official declarations that follow. The track record builds from this sealed record, not from assertion.',
        points: [
          'A forecast record’s hash is anchored to the Bitcoin chain, so it cannot be rewritten after the fact.',
          'The moment a signal was first seen is fixed before any official declaration, so lead time counts only in real time.',
          'View spikes and case-count updates are not used as ground truth, so the system does not score its own signals with itself.',
        ],
      },
      {
        title: 'Known limits',
        kicker: 'KNOWN LIMITS',
        tone: 'amber',
        items: [
          { title: 'Collection gaps', body: 'Signals may be missing for some countries and periods. The system reports by itself which stretches are empty.', meta: 'Gaps are shown, not hidden' },
          { title: 'Alert thresholds', body: 'How sensitive an alert should be is operating policy, not a technical answer. We do not put forward a single “correct” threshold.', meta: 'An operating point the organisation chooses' },
          { title: 'Machine extraction', body: 'PDF-table extraction can misread, so cross-checking against the source is applied and unconfirmed values are flagged separately.', meta: 'Unverified values are marked' },
          { title: 'Local-language processing', body: 'Instead of automatic translation, a language-model classifier and keyword matching are used — a choice made to keep disease names from vanishing or reversing in translation.', meta: 'A design choice for accuracy' },
        ],
      },
      {
        title: 'Why we disclose limits first',
        body: 'AEGIRON is not bound by customer contracts to keep, so it can disclose its limits first — and that becomes a basis for trust that due diligence can verify directly. The first thing reinsurers and government evaluators check is whether an organisation knows its own limits precisely.',
      },
    ],
    cta: {
      title: 'If you find something wrong',
      body: 'If anything on this page is inaccurate, or a limit is missing, please tell us. We will verify it and reflect it.',
      label: 'Contact us',
      href: 'contact',
    },
  },

  dataSources: {
    metaTitle: 'Data sources — all 23 operational sources, disclosed',
    metaDescription:
      'The 23 data sources AEGIRON collects every hour, grouped by type — what each one shows, with how often its origin updates.',
    eyebrow: 'DATA SOURCES',
    title: '23 data sources',
    lead: 'A judgement cannot be checked if its evidence is hidden. Every operational collection source is listed here by type, without exception, together with what each one shows.',
    blocks: [
      {
        title: 'Official health authorities',
        kicker: 'OFFICIAL',
        tone: 'teal',
        body: 'The most reliable. They go through official confirmation, so they move last and serve as the baseline against which other signals are weighed.',
        items: [
          { title: 'WHO Regional Office for Africa', body: 'Outbreak notices and situation reports for the African region.', meta: 'Origin updates: as issued' },
          { title: 'WHO Regional Office for the Americas (PAHO)', body: 'Epidemiological alerts and updates for the Americas.', meta: 'Origin updates: as issued' },
          { title: 'Korea Disease Control and Prevention Agency', body: 'Weekly notification counts for all 45 notifiable infectious diseases in Korea.', meta: 'Origin updates: weekly' },
          { title: 'Japan Infectious Diseases Weekly Report (IDWR)', body: 'Weekly sentinel surveillance counts from Japan’s National Institute of Infectious Diseases.', meta: 'Origin updates: weekly' },
          { title: 'Hong Kong Centre for Health Protection', body: 'Communicable-disease surveillance notices and regular avian-influenza reports.', meta: 'Origin updates: as issued' },
          { title: 'Brazil InfoDengue', body: 'City-level dengue effective reproduction numbers and alert levels.', meta: 'Origin updates: weekly' },
        ],
      },
      {
        title: 'Academic and specialist sources',
        kicker: 'ACADEMIC',
        tone: 'sky',
        body: 'Can move before official announcements. On their own they never raise an alert tier; they carry weight only when they coincide with other layers.',
        items: [
          { title: 'CDC Emerging Infectious Diseases', body: 'The US CDC journal of emerging infectious diseases.', meta: 'Origin updates: as published' },
          { title: 'CIDRAP', body: 'Disease-specific reporting from the University of Minnesota’s Center for Infectious Disease Research and Policy.', meta: 'Origin updates: as published' },
          { title: 'PubMed', body: 'Trends in the number of papers on specific pathogens.', meta: 'Origin updates: daily' },
          { title: 'medRxiv', body: 'Counts of medical preprints posted before peer review.', meta: 'Origin updates: daily' },
        ],
      },
      {
        title: 'Reporting and public attention',
        kicker: 'REPORTING',
        tone: 'crimson',
        body: 'The fastest signal. Also the noisiest, so these sources carry low reliability and are always read against other axes.',
        items: [
          { title: 'Local-language reporting', body: 'News aggregation feeds for 178 countries in 52 languages (179 feeds); ambiguous feeds are re-classified with a language model.', meta: 'Origin updates: hourly' },
          { title: 'NewsWatch', body: 'Trends in major infectious-disease reporting, read from summarised web search results.', meta: 'Origin updates: hourly' },
          { title: 'Naver search trends', body: 'Search ratios for influenza, COVID-19 and Ebola in Korea.', meta: 'Origin updates: daily' },
          { title: 'Mastodon', body: 'Number of people posting under disease hashtags (rolling seven-day window).', meta: 'Origin updates: hourly' },
          { title: 'Wikipedia page views', body: 'Views of Ebola-related articles.', meta: 'Origin updates: daily' },
          { title: 'Polymarket', body: 'Prediction-market prices on a new pandemic — a collective judgement, not evidence.', meta: 'Origin updates: hourly' },
        ],
      },
      {
        title: 'Environment, animals and preparedness behaviour',
        kicker: 'ENVIRONMENT',
        tone: 'forest',
        body: 'These look at outbreak conditions and preparedness behaviour rather than outbreaks themselves — leading signals that can move first when other axes are quiet.',
        items: [
          { title: 'Wastewater surveillance (CDC NWSS)', body: 'Pathogen concentrations at US wastewater treatment plants — a signal from before symptoms appear.', meta: 'Origin updates: weekly' },
          { title: 'WAHIS animal disease', body: 'Animal outbreak reports from the World Organisation for Animal Health — the animal stage of zoonotic disease.', meta: 'Origin updates: as issued' },
          { title: 'Disaster watch window (GDACS)', body: 'After floods, earthquakes or cyclones, the affected country is watched at a lower threshold while disease risk is elevated.', meta: 'Origin updates: as issued' },
          { title: 'Polar observation', body: 'Signals related to permafrost thaw and avian influenza in polar regions — an observation layer, not an alert.', meta: 'Origin updates: daily' },
          { title: 'Supply-chain signals', body: 'Search trends related to demand for medicines such as fever reducers and masks.', meta: 'Origin updates: daily' },
        ],
      },
      {
        title: 'Genomics and countermeasures',
        kicker: 'GENOMICS',
        tone: 'violet',
        items: [
          { title: 'Nextstrain lineage tracking', body: 'Dominant-lineage composition and the emergence of new lineages from reanalysed public sequences. Builds that have stopped updating are not used.', meta: 'Origin updates: varies by build' },
          { title: 'VALHALLA countermeasure data', body: 'Public material on countermeasure readiness: the WHO prequalification list, ClinicalTrials.gov and Korean public procurement notices (KONEPS).', meta: 'Origin updates: mixed daily and monthly' },
        ],
        note: 'As of the 2026-10-18 operational source-health check. How many sources are healthy right now is shown live by the status badge on the home page.',
      },
    ],
    cta: {
      title: 'Check the current state of each source',
      body: 'The dashboard shows each source’s latest collection status and the indicators its signals produce.',
      label: 'Open the live dashboard',
      href: '/dashboard',
    },
  },

  methodology: {
    metaTitle: 'Methodology — a four-layer structure',
    metaDescription:
      'AEGIRON’s methodology in four layers — collection, extraction, analysis and forecasting: established academic methods packaged as an operational product.',
    eyebrow: 'METHODOLOGY',
    title: 'A methodology in four layers',
    lead: 'We did not invent new mathematics. We packaged methods already established in infectious-disease and surveillance epidemiology into a product that runs automatically every day — and we state the standard each layer follows.',
    blocks: [
      {
        title: 'Layer 1 · Collection',
        kicker: 'LAYER 01',
        tone: 'teal',
        body: 'Twenty-three collection sources of very different kinds are normalised into one signal format. Because reliability differs by origin, each value is stored with its reliability, which is used as a weight in every later calculation.',
      },
      {
        title: 'Layer 2 · Extraction',
        kicker: 'LAYER 02',
        tone: 'sky',
        body: 'Structured figures are extracted from unstructured documents (PDF tables and article text). Document images are interpreted block by block, and extracted numbers are cross-checked against the source text. Values that cannot be confirmed in the source are marked unverified.',
      },
      {
        title: 'Layer 3 · Analysis',
        kicker: 'LAYER 03',
        tone: 'crimson',
        body: 'It follows surveillance-epidemiology standards. Anomalies are judged by z-scores against each country’s baseline and by CDC EARS-family methods; performance is assessed by sensitivity, specificity, positive predictive value and false-alarm rate.',
        points: [
          'Sensitivity (POD) = the share of real outbreaks that were caught',
          'Specificity = the share of normal periods judged normal',
          'False-alarm rate (FAR) = the share of alerts that were false',
          'The right false-alarm rate is **operating policy,** not a technical question. How many alerts people can review in a day, and how the cost of a miss compares with the cost of a false alert, are decided by the organisation. So we do not put forward a single “correct” threshold.',
        ],
      },
      {
        title: 'Layer 4 · Forecasting',
        body: 'Spread paths are estimated with a standard SEIR compartmental model plus time-varying interventions. Disease-specific parameters come from measurements in the literature.',
        points: [
          'For contact-limited pathogens, the **reachable population** is constrained. Applying Ebola’s R0 of 1.8 to an entire population produces 87 times the largest outbreak on record — it actually did, and we fixed it.',
          'The effect of an intervention is judged by whether the effective reproduction number falls below 1.',
          'Every result is labelled a “model scenario”, with the historical comparison attached.',
        ],
      },
      {
        title: 'Where this methodology stands',
        body: 'Infectious-disease modelling that combines forecasting and simulation has been practised for over a decade by groups such as Imperial College’s MRC GIDA and Northeastern’s MOBS Lab. What AEGIRON built is not a method but **the structure that runs those methods automatically every day as a commercial product.** We do not claim to be the first in the world.',
      },
    ],
  },

  solutionsReinsurance: {
    metaTitle: 'For reinsurance and insurance',
    metaDescription:
      'Country exposure indices and portfolio comparison. Every response states that these are relative indicators, not absolute probabilities.',
    eyebrow: 'FOR REINSURANCE',
    title: 'Reinsurance and insurance',
    lead: 'The place where pandemic risk used to be quantified is empty. What we provide, however, are relative indicators rather than probabilities — and that distinction is enforced in every response.',
    blocks: [
      {
        title: 'What we provide',
        tone: 'indigo',
        items: [
          { title: 'Country exposure index', body: 'A 0–100 index combining signal pressure, vulnerability and spread potential, for comparing and ranking countries.' },
          { title: 'Portfolio comparison', body: 'The countries you hold, in one view, by relative percentile.' },
          { title: 'Intervention counterfactuals', body: 'Model-based comparison of intervention scenarios against no response.' },
          { title: 'Sealed forecast record', body: 'Forecasts are sealed at creation, so a verifiable record accumulates over time.' },
        ],
      },
      {
        title: 'What you must know',
        accent: true,
        points: [
          'The exposure index is **not an absolute probability.** Every response carries `is_probability: false`.',
          'The weights are policy values, not empirically calibrated ones — stated as `weights_calibrated: false`.',
          'There is no validated forecast record yet. It is not ready to be used directly in pricing.',
        ],
      },
    ],
    cta: {
      title: 'You can start with due diligence',
      body: 'The whole system is open. Verify it first, then discuss the scope of adoption.',
      label: 'Contact us',
      href: 'contact',
    },
  },

  solutionsGovernment: {
    metaTitle: 'For government and public health',
    metaDescription:
      'Import-route tracking and intervention scenario comparison — the effect of each defensive measure, compared with a model.',
    eyebrow: 'FOR GOVERNMENT',
    title: 'Government and public health',
    lead: 'We look at both the routes by which an outbreak abroad enters the country and which measures actually bring transmission under control.',
    blocks: [
      {
        title: 'What we provide',
        tone: 'forest',
        items: [
          { title: 'Import-route tracking', body: 'Import-risk routes estimated from air connectivity and city-level weights.' },
          { title: 'Intervention scenario comparison', body: 'Combinations of isolation, distancing, vaccination and treatment are tested to find the smallest one that brings the effective reproduction number below 1.' },
          { title: 'Hospital-load estimates', body: 'Days of hospital overload estimated from the epidemic curve.' },
          { title: 'Daily briefings', body: 'An automatically generated daily situation summary. On quiet days, it says it was quiet.' },
        ],
      },
      {
        title: 'What you must know',
        accent: true,
        points: [
          'Scenario figures are **estimates under model assumptions.** Review by an epidemiologist is needed before using them as a basis for policy.',
          'The system attaches its own warning to values outside the range explained by historical comparison.',
        ],
      },
    ],
    cta: {
      title: 'Everything needed for an evaluation is public',
      body: 'Review the system, the methodology and the limits first, then discuss the scope of a pilot.',
      label: 'Contact us',
      href: 'contact',
    },
  },

  solutionsNgo: {
    metaTitle: 'For multilateral and humanitarian organisations',
    metaDescription:
      'Early signals from regions with weak surveillance — including countries that others rarely cover because they are commercially unattractive.',
    eyebrow: 'FOR MULTILATERAL & HUMANITARIAN',
    title: 'Multilateral and humanitarian',
    lead: 'The weaker the surveillance, the later the signal arrives. AEGIRON put precisely the regions that existing services rarely cover — for lack of commercial incentive — into its scope from the start.',
    blocks: [
      {
        title: 'What we provide',
        items: [
          { title: 'Priority on vulnerable regions', body: 'Includes countries with large surveillance gaps, such as Nigeria, Ethiopia, Yemen, Madagascar and Papua New Guinea.' },
          { title: 'First local-language reports', body: 'Local reporting before the international press picks an event up.' },
          { title: 'Unexplained-event detection', body: 'Clusters not explained by any known disease are flagged separately.' },
          { title: 'Collection-gap reporting', body: 'The system reports by itself which regions and periods are empty — information the field needs in its own right.' },
        ],
      },
      {
        title: 'What you must know',
        accent: true,
        points: [
          'The weaker a region’s surveillance, **the more likely our own data is empty too.** Gaps are shown, not hidden.',
          'Local-language processing is keyword-based rather than automatic translation, because automatic translation failed our quality validation.',
        ],
      },
    ],
    cta: {
      title: 'We are looking for field partners',
      body: 'Connecting with organisations that reach field signals directly is AEGIRON’s most important next step.',
      label: 'Contact us',
      href: 'contact',
    },
  },

  briefings: {
    metaTitle: 'Daily briefings',
    metaDescription:
      'Infectious-disease situation briefings generated automatically by AEGIRON every day. On quiet days, the briefing says it was quiet.',
    eyebrow: 'BRIEFINGS',
    title: 'Daily briefings',
    lead: 'Generated automatically every day. Because no one edits them by hand, a day without notable events is recorded as a day without notable events.',
    blocks: [
      {
        title: 'How they are produced',
        body: 'The signals collected that day and each country’s risk level are assembled into a summary. The format varies from day to day (bulletin, in-depth, field, data, conversation). Every figure in a briefing is a value the system actually received that day.',
        note: 'A briefing is a summary, not a forecast. When a judgement about a specific country is needed, check the evidence directly on the dashboard.',
      },
    ],
    cta: {
      title: 'What the system is watching today',
      body: 'The dashboard shows the signals behind each briefing as they are.',
      label: 'Open the live dashboard',
      href: '/dashboard',
    },
  },

  about: {
    metaTitle: 'About — AEGIRON',
    metaDescription:
      'AEGIRON builds a global early-warning system that catches infectious-disease signals before they become international news. Busan, South Korea.',
    eyebrow: 'ABOUT',
    title: 'AEGIRON',
    lead:
      'On 31 December 2019, health authorities in Wuhan, China, reported a cluster of pneumonia cases of unknown cause. The World Health Organization declared a public health emergency of international concern a month later. It was not that there were no signals during that month. They were there — in local languages, in places international surveillance rarely looks.\n\nAEGIRON was started to close that gap. It gathers, in the original language, the traces that move before official announcements — local-language news, search volume, wastewater, trade, animal-disease signals — and computes every hour where in the world something departs from normal. Every forecast we make is sealed the moment it is created and then published, so anyone can check whether it was right or wrong.',
    photo: {
      src: '/media/photos/earth-at-night.jpg',
      alt: 'Earth at night — city lights across the Americas (satellite composite)',
      caption: 'Earth at night (Black Marble). A composite of satellite observations.',
      credit: 'NASA Earth Observatory · Public domain',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:Black_Marble_Americas.jpg',
      position: 'center 40%',
    },
    blocks: [
      {
        title: 'What we build',
        kicker: 'WHAT WE BUILD',
        tone: 'teal',
        body: 'We fold local-language reporting from 178 countries, official surveillance data, and environmental, trade and genomic signals into a single index, judge each country’s anomaly against its own baseline, and — the moment an alert is raised — compute spread scenarios and intervention effects alongside it. The design axis is to not stop at detection but to answer “so what, and at what strength”.',
        points: [
          'Detect → judge → forecast → simulate → prescribe → self-verify → seal. The whole chain sits inside one system.',
          'Every forecast is scored automatically against the official declarations that follow, and sealed at the moment it is made so it cannot be edited after the fact.',
          'Two internal R&D programs — defensive genomic screening (HEIMDALL) and countermeasure readiness (VALHALLA) — carry the national-biosecurity axis.',
        ],
      },
      {
        title: 'Where we stand',
        kicker: 'WHERE WE ARE',
        tone: 'indigo',
        body: 'The system actually runs. Signals arrive from the data sources every hour, and the live dashboard is open right now with no login. We are looking for a first partner, and we state that plainly — openness and verifiability are the strengths of this stage.',
        points: [
          '116 modules and 126 endpoints run every hour, and only code that passes 2,201 automated tests ships.',
          'The system, methodology, data and limits are all open from the start, kept in a state due diligence can verify directly.',
          'Every forecast is sealed and accrues, so a verifiable record grows on its own as operation continues.',
        ],
      },
      {
        title: 'Why we publish everything',
        kicker: 'WHY OPEN',
        tone: 'forest',
        body: 'Open everything now, and you stay ready to be checked. It is also a choice a larger competitor cannot structurally copy — they have customer contracts to protect; AEGIRON can open because it has none. The openness itself becomes the basis for trust.',
        note: 'Our validation status and known limits are set out in full on a separate page.',
      },
      {
        title: 'Where we are headed',
        kicker: 'ROADMAP',
        tone: 'violet',
        items: [
          { title: 'Short term', body: 'Connect with real field organisations and surveillance networks to get closer to the source of the signal. Reinsurers, governments, international bodies and field organisations are the first candidate partners.' },
          { title: 'Medium term', body: 'Keep operating to accumulate a verifiable forecast record. The sealed record is the basis for “we really did forecast it, then”.' },
          { title: 'Long term', body: 'To become global early-warning infrastructure actually used in regions where surveillance is thin.' },
        ],
      },
    ],
    cta: {
      title: 'We are looking for people to talk with',
      body: 'Reinsurance, government, international bodies, field organisations — all welcome. You can see the whole system first, without booking a demo.',
      label: 'Get in touch',
      href: 'contact',
    },
  },

  contact: {
    metaTitle: 'Contact',
    metaDescription: 'How to reach AEGIRON.',
    eyebrow: 'CONTACT',
    title: 'Contact',
    lead: 'You can review the whole system without booking a demo. If, after reviewing it, you have questions or a proposal for collaboration, please reach us below.',
    blocks: [
      {
        title: 'Details',
        items: [
          { title: 'Email', body: 'kimdaeheuk@gmail.com', meta: 'The fastest route' },
          { title: 'Location', body: 'Busan, South Korea', meta: 'KST (UTC+9)' },
        ],
      },
      {
        title: 'Especially welcome',
        points: [
          '**Corrections** — tell us about errors in our methodology or figures and we will verify and reflect them.',
          '**Connections to field organisations** — a route into real surveillance networks is our most important next step.',
          '**Pilot discussions** — reinsurers, governments, international bodies and field organisations are all welcome.',
        ],
      },
    ],
  },

  privacy: {
    metaTitle: 'Privacy policy',
    metaDescription: 'Privacy policy for the AEGIRON website.',
    eyebrow: 'LEGAL',
    title: 'Privacy policy',
    lead: 'This site does not require visitors to log in and does not collect personal information.',
    blocks: [
      {
        title: 'What we do not collect',
        points: [
          'There is no sign-up or login, so no account information is collected.',
          'This site uses no advertising or visitor-analytics tracking tools.',
          'Viewing the dashboard requires no personally identifying information.',
        ],
      },
      {
        title: 'External services',
        body: 'The introduction video on the home page is embedded in YouTube’s privacy-enhanced mode; YouTube’s policies apply once it is played. Fonts are loaded from Google Fonts and jsDelivr, so those services may record access data such as IP addresses.',
      },
      {
        title: 'When you contact us',
        body: 'If you email us, the content and your address are used only to reply and are never shared with third parties.',
      },
      {
        title: 'Changes',
        body: 'If this policy changes, this page will be updated.',
      },
    ],
  },

  terms: {
    metaTitle: 'Terms of use',
    metaDescription: 'Terms for using the AEGIRON website and its public data.',
    eyebrow: 'LEGAL',
    title: 'Terms of use',
    lead: 'The conditions that apply when you use this site and the public dashboard.',
    blocks: [
      {
        title: 'Nature of the information provided',
        accent: true,
        points: [
          'Information on this site is **for reference only** and is not provided as a basis for medical, public-health or investment decisions.',
          'Forecast and scenario figures are **estimates under model assumptions** — neither measurements nor guarantees.',
          'AEGIRON does not yet hold a validated track record for early-detection accuracy.',
          'AEGIRON accepts no liability for the consequences of decisions based on this information.',
        ],
      },
      {
        title: 'Data sources',
        body: 'This system collects and processes public material from bodies such as the WHO and the CDC. Copyright and terms of use for the original material remain with each body. Processed figures may differ from the originals, so always consult the originating body’s material when an official citation is needed.',
      },
      {
        title: 'Availability',
        body: 'The public dashboard may be suspended or changed without notice.',
      },
    ],
  },
};
