import type { PagesDict } from '../types';

/**
 * English subpage content.
 *
 * ★ Figures here are measured values ★
 * 23 operational collection sources · 114 algorithm modules · 123 endpoints · 2,145 automated tests (measured 2026-10-18).
 *
 * ★ HARD RULE ★ No accuracy or lead-time claims.
 */
export const pagesEn: PagesDict = {
  platform: {
    metaTitle: 'System — from signal to alert',
    metaDescription:
      'The five stages through which AEGIRON turns infectious-disease signals into alerts — collect, extract, judge, forecast, respond — and what each stage deliberately discards.',
    eyebrow: 'SYSTEM',
    title: 'From signal to alert',
    lead: 'The quality of a surveillance system is decided less by what it catches than by what it discards. For each of the five stages, we state what we keep and what we throw away.',
    blocks: [
      {
        title: '01 · Collect',
        body: 'Signals arrive every hour from 23 operational collection sources. Material of very different kinds is mixed together — from official reports of international bodies to local-language reporting from 179 countries — so each source is stored with its own reliability weight, which every later calculation carries forward.',
        items: [
          { title: 'Official reporting', body: 'WHO regional offices for Africa and the Americas, the Korea Disease Control and Prevention Agency, Japan’s infectious-disease weekly report, Hong Kong’s Centre for Health Protection and Brazil’s InfoDengue. We use each body’s own severity grade and never invent one.' },
          { title: 'Local-language reporting', body: 'Local coverage before the international press takes an event up — including countries that other surveillance services rarely cover because they are commercially unattractive.' },
          { title: 'Environmental and indirect signals', body: 'Wastewater surveillance (US CDC NWSS), a disaster watch window (GDACS), polar observation and medical-supply trade statistics. These are proxies for outbreak conditions and preparedness behaviour, not for outbreaks themselves.' },
        ],
        note: 'Trade statistics are reported with a lag of roughly two months and are not a real-time indicator. Every response says so.',
      },
      {
        title: '02 · Extract',
        body: 'Disease, country, cases and deaths are structured from PDF tables and article text. One rule governs this stage: what cannot be read is left empty, never guessed.',
        points: [
          'A column whose table header cannot be read is **discarded.** Filling it by position makes numbers drift silently.',
          '“New in the last seven days” and “cumulative” are kept as separate fields. Mixing them reports 296 new cases as a cumulative 1,437.',
          '“Probable or suspected” and “confirmed” sit on separate axes. Combining them turns suspected patients into a confirmed total.',
          'A “total” row is not a country and is excluded — otherwise a country called `Total` appears and contaminates trend analysis.',
        ],
        note: 'Machine-extracted values can be misread. Extracted numbers are cross-checked against the source text, and values that cannot be confirmed there are flagged separately.',
      },
      {
        title: '03 · Judge',
        body: 'Anomalies are computed **against each country’s usual level,** not in absolute terms. The same five cases mean something different in a country that reports constantly and in one that is usually quiet.',
        points: [
          'The anomaly score is the deviation from each country’s baseline.',
          'Older signals contribute less over time (half-life decay).',
          '“Measured and found normal” is reported separately from “no data to judge” — mixing the two makes quiet periods read as alerts.',
        ],
      },
      {
        title: '04 · Forecast',
        body: 'Transmission models estimate the scale of spread and the risk of import. Every value carries its assumptions and limits.',
        points: [
          'Models are fitted with disease-specific R0 and fatality rates from the literature.',
          'For pathogens that have never produced a generalised epidemic, the **reachable population** is constrained. An R0 above 1 does not mean the whole population is infected.',
          'Modelled death estimates are checked automatically against the largest outbreaks on record; when a value exceeds the explainable range, **a warning travels with the number.**',
        ],
        note: 'Scenario figures are estimates under model assumptions — neither measurements nor guarantees.',
      },
      {
        title: '05 · Respond',
        body: 'We do not stop at “what is coming”. No-response and intervention scenarios are compared to show which measures bring transmission under control.',
        items: [
          { title: 'Against no response', body: 'The path with no measures taken is kept as the baseline.' },
          { title: 'Comparing interventions', body: 'Combinations of isolation, distancing, vaccination and treatment are tested to find where the effective reproduction number falls below 1.' },
          { title: 'Sealing', body: 'Forecasts and scenarios are sealed with a hash at the moment they are produced. This proves not that they were right, but that we held this content at this time.' },
        ],
      },
    ],
    cta: {
      title: 'The working system is faster than any description',
      body: 'You can open the screen where these five stages actually run, right now.',
      label: 'Open the live dashboard',
      href: '/dashboard',
    },
  },

  techSpec1: {
    metaTitle: 'Technology I — the always-on surveillance layer',
    metaDescription:
      'The engines that run automatically every hour: local-language news surveillance, the six-layer anomaly index, reporting-silence watch, unexplained clusters, CDC EARS aberration detection, and silent-failure monitoring. Each engine’s method and limits, stated plainly.',
    eyebrow: 'TECHNOLOGY · I',
    title: 'The always-on surveillance layer',
    lead: 'Of AEGIRON’s 114 algorithm modules, these are the ones that run by themselves every hour, with no one asking. Their job is to keep counting what differs from normal. For each engine we state what it treats as its baseline, and what it deliberately refuses to count.',
    photo: {
      src: '/media/photos/iss-city-lights.jpg',
      alt: 'City lights at night seen from the International Space Station',
      caption: 'Türkiye at night, seen from the International Space Station. The networks that move people and goods are the same routes an outbreak travels.',
      credit: 'NASA JSC · Public domain',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:The_city_lights_of_T%C3%BCrkiye_sparkle_below_the_International_Space_Station_(iss074e0225549).jpg',
    },
    blocks: [
      {
        title: 'Local-language news surveillance',
        body: 'Before the international press translates it, the first signal is often a report in the local language. We take 179 countries from news aggregated by country and language, measure the density of disease vocabulary, and re-classify ambiguous feeds with a language model. We do not curate low-risk countries out — a pandemic can begin anywhere, and quiet countries are left dormant by downstream thresholds, not by us.',
        points: [
          'The unit of detection is the intersection of country, language and disease — one country seen through a single aggregation window, not scattered outlets.',
          'The final high-alert call is led by the language-model classifier, with keywords as the fallback — keywords alone let unrelated articles through.',
          'When several feeds report the same event, we group them as overlapping and exclude them from the alert.',
        ],
        note: 'Feeds with too little data are separated out as “undetermined”, not raised as alerts. We do not quietly pass over the fact that the data is thin.',
      },
      {
        title: 'Six-layer anomaly index',
        body: 'Signals from six layers — official, unofficial, behavioural, environmental, animal and unexplained — are each converted into an anomaly score against their own usual level, weighted by source reliability, and combined into one index. The reference is each indicator’s baseline, not its absolute volume: the same count means different things in a country that reports heavily and one that is usually quiet.',
        points: [
          'Each signal is scored as a deviation (z-score) from its own historical distribution, with the latest value excluded from the baseline.',
          'Each layer carries a different source-reliability weight — an official government API and a count of social posters cannot weigh the same.',
          'Older signals contribute less over time (half-life decay).',
        ],
        note: 'This index only looks at increases. The downside — a channel that falls silent — is handled by the reporting-silence watch below.',
      },
      {
        title: 'Reporting-silence watch',
        body: 'It is not only rising signals that are dangerous. When a normally active reporting channel suddenly goes quiet, that itself is a signal — the reporting system may have collapsed. In the 2014 Guinea Ebola outbreak, ministry reporting fell first; weeks after the WHO read it as “quiet”, it exploded.',
        points: [
          'A channel qualifies when today’s value drops below half of its historical average.',
          'Only indicators with an explicitly declared decision rule are watched — an allow-list design, so that a “0” from a report not yet filed is not mistaken for a collapse.',
        ],
        note: 'This design is the result of a redesign after the layer raised four false alerts during pre-launch soak in 2026-09. We kept the failure on the record and fixed it.',
      },
      {
        title: 'Unexplained clusters',
        body: 'Among the clusters extracted from reporting, we separately count those that do not match any known disease pattern. The December 2019 cluster of pneumonia of unknown cause in Wuhan is the archetype — the aim is to catch “this is unlike the rest” before it has a name.',
        points: [
          'At extraction time we ask the language model directly whether the case matches a known disease pattern. We do not force something into the unexplained bin merely because it is absent from a small alias dictionary.',
          'When the same event returns with only its wording changed, we group it at the country level so the same alert does not fire again every day.',
        ],
        note: 'Of the three conditions the handover document proposed, a surge in hospital visits cannot be measured — there is no source for it. We leave it empty rather than fill it with a fabrication.',
      },
      {
        title: 'Standard aberration detection · silent-failure watch',
        body: 'We layer on the surveillance-epidemiology standard (the US CDC’s EARS C1/C2/C3), which works even when the baseline is short. Above it sits one more layer — counting, every cycle, whether a source actually returned a value and whether the method that produced it still holds.',
        items: [
          { title: 'CDC EARS', body: 'Three windows (C1, C2, C3) ask how many σ today’s value sits above the recent baseline. A guard band keeps early outbreak values from contaminating the baseline.', meta: 'A US CDC operational standard' },
          { title: 'Source health', body: 'A source whose collection ran but returned nothing is not counted as healthy. Sources that succeed only occasionally are flagged separately.', meta: 'A silently dead source is the most dangerous failure' },
          { title: 'Quality invariants', body: 'Counts the cases where the source is fine but the computation that produced its value has broken. All six incidents in 2026-08 were of this type.', meta: 'A layer source-health structurally cannot see' },
        ],
      },
    ],
    cta: {
      title: 'The deeper engines are in Technology II',
      body: 'Genomic screening, cross-border spread simulation, per-alert intervention scenarios, automatic forecast scoring — the layer that runs on request or on alert.',
      label: 'See Technology II',
      href: 'technology-advanced',
    },
  },

  techSpec2: {
    metaTitle: 'Technology II — genomics, simulation, response, self-verification',
    metaDescription:
      'The deep engines that run on request or on alert: measured sequence-order naturalness, homology-based chimera detection, cross-border spread simulation, import-date estimation, per-alert intervention scenarios, automatic forecast scoring, and forecast sealing — each with its measured basis and its limits.',
    eyebrow: 'TECHNOLOGY · II',
    title: 'Genomics · simulation · response · self-verification',
    lead: 'If the always-on layer counts what differs, this layer answers what to do about it, and how. Most of it computes on request or on alert — it is heavy, and there is no reason to run it every hour. Every number carries, alongside it, how far it can be trusted.',
    photo: {
      src: '/media/photos/avian-influenza-h5n1.jpg',
      alt: 'Colorized transmission electron micrograph of avian influenza A(H5N1) virus particles',
      caption: 'Avian influenza A(H5N1) virus particles, colorized transmission electron micrograph. Public material from the US CDC.',
      credit: 'CDC / Cynthia Goldsmith · Public domain',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:Colorized_transmission_electron_micrograph_of_Avian_influenza_A_H5N1_viruses.jpg',
    },
    blocks: [
      {
        title: 'Genomics — order naturalness',
        body: 'Composition statistics (GC, CpG, codon usage) look only at the make-up of the bases. They miss a sequence whose composition is natural but whose order is not — spliced or recombined. We give a genomic foundation model only the start of a sequence, have it predict the next bases, and measure order naturalness directly by agreement with the real sequence.',
        points: [
          'Measured (2026-07): natural sequences agree closely, and shuffling the order while keeping composition identical makes agreement collapse — it catches the angle composition statistics cannot.',
          'It produces a “priority for further review”, not a verdict. Low agreement does not by itself mean an engineered sequence.',
        ],
        note: 'This model excluded eukaryotic-host viruses from training, so it is not applied to coronavirus, influenza or Ebola sequences — the applicable domain is declared, and outside it the score is reported but no flag is raised.',
      },
      {
        title: 'Genomics — homology-based chimera detection',
        body: 'To avoid a trained model’s blind spot (taxa left out of training), we search a protein sequence against public homology databases to see whether any natural protein covers the full length of the query. For a natural protein, close relatives cover the whole span; for a sequence stitched from fragments of several organisms, no natural protein covers all of it — the direct trace of recombination.',
        points: [
          'Because it is a database search and not a model, it works on viruses too.',
          'The thresholds were pre-registered so that a false-positive test — deliberately including under-studied pathogens — passes.',
        ],
        note: 'Low coverage is a “not fully explained by natural homologues” review priority, not an artificial verdict. The final judgement needs an expert, phylogenetics and wet-lab work.',
      },
      {
        title: 'Simulation — cross-border spread',
        body: 'A metapopulation SEIR model with 159 countries as nodes, and 1,671 air-linked country pairs and 314 land borders as edges. It reports countries not reached within the period separately from countries for which no route is known at all — “safe” and “unknown” are not the same word.',
        items: [
          { title: 'Import-date estimate', body: 'From the origin city’s international passenger volume, flight time and early exponential growth, it estimates the days to a first imported case and the risk at each port of entry.', meta: 'A model estimate, not an observed import date' },
          { title: 'Network limits', body: 'The air network is 2014 public route data. Whether two countries are connected changes little, but frequencies have changed a lot, and land traffic is a population-based estimate.', meta: 'Surfaced with the result as air_network_coverage' },
        ],
      },
      {
        title: 'Response — per-alert intervention scenarios',
        body: 'Until now an alert ended at “what is coming”. The recipient got no answer to “so what do we do”. For every new critical or high alert, we run an SEIR defence simulation with disease-specific parameters and attach the difference between no response and intervention, in deaths and days of hospital overload — the step that turns a forecasting tool into a decision tool.',
        points: [
          'Transmission coefficients and fatality rates are representative values from the literature. Before calibration to the actual pathogen and region, they are a directional reference — we say “N under model assumptions”, never “saves N”.',
          'For an alert where the disease cannot be identified, we produce no numbers. A death toll invented from generic constants would be a number with no basis.',
        ],
      },
      {
        title: 'Self-verification — scoring and sealing',
        body: 'The claim to “know before others” is a sales line unless there is a path to prove it. So we put the verification in the code. Recorded forecasts are scored every day against the official declarations that follow, and every forecast is sealed at the moment it is made.',
        items: [
          { title: 'Automatic forecast scoring', body: 'Unresolved forecasts are checked daily against official declarations and sorted into hit, miss or undetermined. Spikes in views and case-count updates are not used as ground truth — that would be scoring our signals with our own signals.', meta: 'If measured lead time is 0, we say 0' },
          { title: 'Lead-time ledger', body: 'It fixes the moment a signal was first seen before any official declaration. A lead time found by searching backwards after a declaration is not accepted as a measurement.', meta: 'It separates after-the-fact loading from real time' },
          { title: 'Forecast sealing', body: 'The hash of a forecast record is anchored in a public timestamp (the Bitcoin chain). A third party can verify for themselves that the forecast was not rewritten later.', meta: 'Evidence of a kind that cannot be applied retroactively' },
        ],
      },
    ],
    cta: {
      title: 'These two layers form one chain',
      body: 'Detect → judge → forecast → simulate → prescribe → self-verify → seal. The screen where that chain actually runs is the live dashboard.',
      label: 'Live dashboard',
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
    metaTitle: 'Validation and limits — what is not yet proven, and the known gaps',
    metaDescription:
      'Everything AEGIRON has not yet validated, its known limits and its data gaps — and the mechanisms by which the system checks its own numbers.',
    eyebrow: 'VALIDATION & LIMITS',
    title: 'Validation and limits',
    lead: 'The most dangerous failure in disease surveillance is not a wrong forecast but one that cannot be checked. So we state first what has not yet been validated and the known limits, and then describe the mechanisms by which the system checks its own numbers.',
    blocks: [
      {
        title: 'Not yet validated',
        accent: true,
        points: [
          '**There is no validated track record for early-detection accuracy.** That is why no claim of “detected days earlier” appears anywhere on this site.',
          'The system went into full operation in 2026. Performance on earlier outbreaks is a **retrospective reconstruction** and is not the same as real-time performance.',
          'Scenario figures from the forecasting modules are **estimates under model assumptions** — neither measurements nor guarantees.',
          'No external body has yet validated the system independently. All performance evaluation so far has been internal.',
        ],
        note: 'These items change as the operating record grows. When they change, this page is updated.',
      },
      {
        title: 'Known limits',
        items: [
          {
            title: 'Collection gaps',
            body: 'Signals are missing for some countries and periods. Where data is empty, no model can forecast an outbreak.',
            meta: 'The system reports by itself which periods are empty',
          },
          {
            title: 'False-alert rate',
            body: 'In the current performance range, many alerts do not lead to an actual outbreak. Alert fatigue is a real cause of failure for early-warning systems.',
            meta: 'Thresholds are treated as operating policy, not as a correct answer',
          },
          {
            title: 'Machine-extraction errors',
            body: 'Numbers read from PDF tables can be misread. Cross-checking against the source text is applied, but it is not complete.',
            meta: 'Unconfirmed values are flagged separately',
          },
          {
            title: 'Translation quality',
            body: 'Automatic translation for local-language articles was tested and rejected: in Swahili and Amharic we found disease names disappearing and meanings reversed.',
            meta: 'Keyword matching stays in place until an alternative is found',
          },
        ],
      },
      {
        title: 'Verification the system performs itself',
        body: 'If limits are written only in documents, the numbers break away and are reused as-is on screens and in reports. So the verification is built into the code.',
        points: [
          '**Historical comparison** — modelled death estimates are compared automatically with the largest outbreak on record for that disease; above ten times that figure, a “do not use in external material” warning is attached to the response.',
          '**Separating causes of failure** — when an outbreak is missed, “the model missed it” is reported separately from “there was no data to see it”. Mixing them inverts the diagnosis.',
          '**Prospective evaluation** — performance is scored only on a future that was unknowable at the time, never on training data. Adding features almost always raises in-sample scores.',
          '**Provenance** — when a disease name or country comes from context rather than a table, where it came from is recorded alongside it.',
        ],
      },
      {
        title: 'Why this page exists',
        body: 'A company bound by customer contracts finds it hard to disclose its weaknesses. AEGIRON is not yet bound in that way, so it can disclose its limits first — and that becomes a basis for trust that due diligence can verify directly. The first thing reinsurers and government evaluators check is whether an organisation knows its own limits precisely.',
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
      'The 23 data sources AEGIRON collects every hour, grouped by type — what each one shows, what it cannot show, and how often its origin updates.',
    eyebrow: 'DATA SOURCES',
    title: '23 data sources',
    lead: 'A judgement cannot be checked if its evidence is hidden. Every operational collection source is listed here by type, without exception, together with what each one cannot see.',
    blocks: [
      {
        title: 'Official health authorities',
        body: 'The most reliable and the slowest, because they go through official confirmation. In early warning they serve as the baseline against which other signals are weighed.',
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
        body: 'Can move before official announcements, but fluctuate with research and publication cycles. On their own they never raise an alert tier; they carry weight only when they coincide with other layers.',
        items: [
          { title: 'CDC Emerging Infectious Diseases', body: 'The US CDC journal of emerging infectious diseases.', meta: 'Origin updates: as published' },
          { title: 'CIDRAP', body: 'Disease-specific reporting from the University of Minnesota’s Center for Infectious Disease Research and Policy.', meta: 'Origin updates: as published' },
          { title: 'PubMed', body: 'Trends in the number of papers on specific pathogens.', meta: 'Origin updates: daily' },
          { title: 'medRxiv', body: 'Counts of medical preprints posted before peer review.', meta: 'Origin updates: daily' },
        ],
      },
      {
        title: 'Reporting and public attention',
        body: 'The fastest and the noisiest. News moves only after a journalist has written a story, so these sources carry low reliability and are always read against other axes.',
        items: [
          { title: 'Local-language reporting', body: 'News aggregation feeds for 179 countries and languages; ambiguous feeds are re-classified with a language model.', meta: 'Origin updates: hourly' },
          { title: 'NewsWatch', body: 'Trends in major infectious-disease reporting, read from summarised web search results.', meta: 'Origin updates: hourly' },
          { title: 'Naver search trends', body: 'Search ratios for influenza, COVID-19 and Ebola in Korea.', meta: 'Origin updates: daily' },
          { title: 'Mastodon', body: 'Number of people posting under disease hashtags (rolling seven-day window).', meta: 'Origin updates: hourly' },
          { title: 'Wikipedia page views', body: 'Views of Ebola-related articles. The origin is currently unstable, so values arrive only intermittently.', meta: 'Origin updates: daily · unstable' },
          { title: 'Polymarket', body: 'Prediction-market prices on a new pandemic — a collective judgement, not evidence.', meta: 'Origin updates: hourly' },
        ],
      },
      {
        title: 'Environment, animals and preparedness behaviour',
        body: 'These look at outbreak conditions and preparedness behaviour rather than outbreaks themselves. They are not direct evidence, but they can move first when other axes are quiet.',
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
        items: [
          { title: 'Nextstrain lineage tracking', body: 'Dominant-lineage composition and the emergence of new lineages from reanalysed public sequences. Builds that have stopped updating are not used.', meta: 'Origin updates: varies by build' },
          { title: 'VALHALLA countermeasure data', body: 'Public material on countermeasure readiness: the WHO prequalification list, ClinicalTrials.gov and Korean public procurement notices (KONEPS). The EU procurement (TED) connection is not yet verified and is not used in any count.', meta: 'Origin updates: mixed daily and monthly' },
        ],
      },
      {
        title: 'Sources removed from tracking',
        body: 'A source that disappears silently is the most dangerous failure in a surveillance system. So sources taken out of operation remain listed, with the reason.',
        items: [
          { title: 'Air mobility (OpenSky)', body: 'Access from cloud servers is blocked, so it could not be received reliably and was removed from tracking. The cross-border spread simulation uses separate public air-route data.', meta: 'Removed from tracking' },
          { title: 'GroqWatch', body: 'Replaced by NewsWatch because of a high failure rate.', meta: 'Removed from tracking · 2026-09-01' },
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
        body: 'Twenty-three collection sources of very different kinds are normalised into one signal format. Because reliability differs by origin, each value is stored with its reliability, which is used as a weight in every later calculation.',
      },
      {
        title: 'Layer 2 · Extraction',
        body: 'Structured figures are extracted from unstructured documents (PDF tables and article text). Document images are interpreted block by block, and extracted numbers are cross-checked against the source text. Values that cannot be confirmed in the source are marked unverified.',
      },
      {
        title: 'Layer 3 · Analysis',
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
      'AEGIRON builds an early-warning system that catches infectious-disease signals before they become international news. Busan, South Korea. We state our current stage and where we are headed, plainly.',
    eyebrow: 'ABOUT',
    title: 'AEGIRON',
    lead: 'A pandemic is never declared out of nowhere. For weeks before the declaration it leaves traces — in local reporting, in search, in wastewater, in trade. AEGIRON gathers those traces before they are translated and computes, every hour, where something differs from normal. We are based in Busan, South Korea.',
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
        body: 'We fold local-language reporting from 179 countries, official surveillance data, and environmental, trade and genomic signals into a single index, judge each country’s anomaly against its own baseline, and — the moment an alert is raised — compute spread scenarios and intervention effects alongside it. The design axis is to not stop at detection but to answer “so what, and at what strength”.',
        points: [
          'Detect → judge → forecast → simulate → prescribe → self-verify → seal. The whole chain sits inside one system.',
          'Every forecast is scored automatically against the official declarations that follow, and sealed at the moment it is made so it cannot be edited after the fact.',
          'Two internal R&D programs — defensive genomic screening (HEIMDALL) and countermeasure readiness (VALHALLA) — carry the national-biosecurity axis.',
        ],
      },
      {
        title: 'Where we stand',
        body: 'We are early-stage. We will not blur that — due diligence surfaces it anyway, and the moment we blur it, the credibility of everything else falls with it.',
        points: [
          'The system actually runs. Signals arrive from the data sources every hour, and the live dashboard is open right now with no login.',
          'We have no commercial customers yet. We are looking for a first partner.',
          'No external body has yet validated the system independently. All performance evaluation so far has been internal.',
          'We hold no validated early-detection track record. With continued operation it accrues on its own, as sealed forecasts.',
        ],
      },
      {
        title: 'Why we publish everything',
        body: 'If, with no customer and no contract, you build things to hide, they all become liabilities when it is time to be validated. Open everything now, and you stay ready to be checked. It is also a choice a larger competitor cannot structurally copy — they have customer contracts to protect; we can open because we have none. The weakness and the strength come from the same place.',
        note: 'Our validation status and known limits are set out in full on a separate page.',
      },
      {
        title: 'Where we are headed',
        items: [
          { title: 'Short term', body: 'Connect with real field organisations and surveillance networks to get closer to the source of the signal. Reinsurers, governments, international bodies and field organisations are the first candidate partners.' },
          { title: 'Medium term', body: 'Keep operating to accumulate a verifiable forecast record. The sealed record is the basis for “we really did forecast it, then”.' },
          { title: 'Long term', body: 'To become early-warning infrastructure actually used in regions where surveillance is thin.' },
        ],
      },
    ],
    cta: {
      title: 'If this seems worth a conversation',
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
