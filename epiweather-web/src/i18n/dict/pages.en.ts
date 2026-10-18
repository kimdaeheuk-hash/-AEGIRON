import type { PagesDict } from '../types';

/**
 * English subpage content.
 *
 * ★ Every figure here is measured as of 2026-08-06 ★
 * 21 sources · 106 endpoints · 81 algorithm modules · 740 automated tests passing ·
 * 217 country reference records. No estimate is presented as a fact.
 *
 * ★ HARD RULE ★ No accuracy or lead-time claims.
 */
export const pagesEn: PagesDict = {
  platform: {
    metaTitle: 'System — from signal to alert',
    metaDescription:
      'The five stages AEGIRON runs — collect, extract, judge, forecast, respond — and what each stage deliberately throws away.',
    eyebrow: 'SYSTEM',
    title: 'From signal to alert',
    lead: 'The quality of a surveillance system is decided less by what it catches than by what it discards. Here is what each of the five stages keeps, and what it drops.',
    blocks: [
      {
        title: '01 · Collect',
        body: 'Signals arrive automatically from 21 sources. Official multilateral reports and local-language news are entirely different kinds of evidence, so each source carries its own trust weight through the rest of the system.',
        items: [
          { title: 'Official reporting', body: 'WHO situation reports and disease outbreak news, Africa CDC, CDC travel health notices. We use each body’s own severity grade — we never invent a severity of our own.' },
          { title: 'Local-language news', body: 'Reporting from before an event reaches international media, including countries commercially unattractive enough that others skip them.' },
          { title: 'Environmental & indirect', body: 'Climate, satellite forest change, trade statistics on protective equipment, wastewater surveillance. These proxy the conditions for an outbreak and the preparations around it, not the outbreak itself.' },
        ],
        note: 'Trade statistics carry roughly a two-month reporting lag, so they are a medium-term indicator, not a real-time one. Every response states this.',
      },
      {
        title: '02 · Extract',
        body: 'Disease, country, cases and deaths are structured out of PDF tables and article text. One rule governs this stage: anything not recognised is left empty rather than guessed.',
        points: [
          'Columns whose header is not understood are **discarded.** Filling them by position makes numbers wrong quietly.',
          '“New in the last 7 days” and “cumulative” are kept apart. Merging them once reported 296 new deaths as a cumulative 1,437.',
          '“Probable/suspected” and “confirmed” are separate axes. Combining them turns suspected cases into a confirmed total.',
          '“Total” rows are excluded — they are not countries. Otherwise a nation called `Total` appears and contaminates every trend.',
        ],
        note: 'These are machine-extracted values and misreads are possible. Extracted numbers are cross-checked against the source text, and anything unconfirmed is flagged as such.',
      },
      {
        title: '03 · Judge',
        body: 'Anomaly is scored **against each country’s own baseline**, not against an absolute count. Five signals mean one thing in a country that reports constantly and something else entirely in a quiet one.',
        points: [
          'Deviation is measured against the country’s own recent history.',
          'Older signals contribute less over time (half-life decay).',
          '“Measured, and nothing unusual” is reported separately from “not enough data to judge” — merging them makes an ordinary week read as an alert.',
        ],
      },
      {
        title: '04 · Forecast',
        body: 'Transmission models estimate scale and importation risk. Every value carries its assumptions and limits.',
        points: [
          'Models are calibrated with disease-specific R0 and case fatality rates from the literature.',
          'For pathogens that have never produced a general epidemic, the **reachable population** is capped. An R0 above 1 does not mean an entire population becomes infected.',
          'Modelled death estimates are compared automatically against the largest outbreak on record, and when the result exceeds a defensible range the **warning travels with the number**.',
        ],
        note: 'Scenario figures are estimates under model assumptions — neither measurements nor guarantees.',
      },
      {
        title: '05 · Respond',
        body: 'The output does not stop at “something is coming”. No-action and intervention scenarios are compared so the answer includes which measures actually bring transmission under control.',
        items: [
          { title: 'No-action baseline', body: 'The trajectory with no measures taken serves as the reference line.' },
          { title: 'Intervention comparison', body: 'Isolation, distancing, vaccination and treatment are combined to find where the effective reproduction number falls below one.' },
          { title: 'Timestamping', body: 'Forecasts and scenarios are hashed and sealed when created. This proves only that we held this content at this time — never that it was correct.' },
        ],
      },
    ],
    cta: {
      title: 'The system explains itself faster than we can',
      body: 'You can open the running version of all five stages right now.',
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
      'Everything AEGIRON has not yet validated, its known limits, and its data gaps — plus how the system checks its own numbers.',
    eyebrow: 'VALIDATION & LIMITS',
    title: 'Validation and limits',
    lead: 'The most dangerous failure in disease surveillance is not a wrong forecast but one nobody can check. So we start with what we are not sure of. If we do not say it, due diligence says it for us.',
    blocks: [
      {
        title: 'Not yet validated',
        accent: true,
        points: [
          '**We have no validated track record for early-detection accuracy.** That is why no claim of the form “detected N days earlier” appears anywhere on this site.',
          'The system entered full operation in 2026. Results for earlier outbreaks are **retrospective reconstructions** and are not equivalent to live performance.',
          'Scenario figures from the forecasting modules are **estimates under model assumptions** — neither measurements nor guarantees.',
          'No external body has independently reviewed this system. So far it has been evaluated only by the people who built it.',
        ],
        note: 'These statements will change over time. When they do, this page changes with them.',
      },
      {
        title: 'Known limits',
        items: [
          {
            title: 'Collection gaps',
            body: 'Signals are missing for some countries and periods. No model can predict an outbreak across a window where nothing was collected.',
            meta: 'The system reports which windows are empty',
          },
          {
            title: 'False alarm rate',
            body: 'At current performance a substantial share of alerts do not become real outbreaks. Alert fatigue is the practical failure mode of early-warning systems.',
            meta: 'Thresholds are treated as operating policy, not as a right answer',
          },
          {
            title: 'Machine extraction errors',
            body: 'Reading numbers out of PDF tables can misfire. Cross-checking against the source text helps but is not complete.',
            meta: 'Unverified values are flagged',
          },
          {
            title: 'Translation quality',
            body: 'We tested automatic translation for local-language articles and rejected it. In Swahili and Amharic we observed disease names disappearing and meanings inverting.',
            meta: 'Keyword matching stays until a better option exists',
          },
        ],
      },
      {
        title: 'So the system checks itself',
        body: 'Limits written only in documentation get separated from the numbers, and the numbers end up in slide decks unqualified. So the checks live in the code.',
        points: [
          '**Historical comparison** — modelled death estimates are compared against the largest recorded outbreak of that disease, and above a factor of ten the response carries an explicit “do not use externally” warning.',
          '**Separating failure modes** — when an outbreak is missed we report “the model failed” apart from “we had no data”. Merging them inverts the diagnosis.',
          '**Prospective evaluation** — performance is scored only on periods the model could not see during training, because adding features almost always improves training scores.',
          '**Provenance** — when a disease name or country comes from surrounding context rather than the table itself, we record where it came from.',
        ],
      },
      {
        title: 'Why this page exists',
        body: 'You will not find this page on a competitor’s site, because a company with customers and contracts cannot easily publish its weaknesses. We have nothing to protect yet, so we can — and that is one of the few real advantages we hold. It is also the first thing a reinsurer’s due diligence looks for: whether the team knows its own limits.',
      },
    ],
    cta: {
      title: 'If you find something wrong here',
      body: 'If anything on this page is inaccurate or a limit is missing, tell us. Corrections get applied.',
      label: 'Get in touch',
      href: 'contact',
    },
  },

  dataSources: {
    metaTitle: 'Data sources — all 21, published',
    metaDescription:
      'Every one of the 21 live data sources AEGIRON uses, grouped by type, with update cadence and limits.',
    eyebrow: 'DATA SOURCES',
    title: '21 data sources',
    lead: 'A judgement cannot be checked if the evidence behind it is hidden. Every source is listed by type — along with what each one cannot do.',
    blocks: [
      {
        title: 'Official health bodies',
        body: 'The most reliable and the slowest, because they pass through formal confirmation. In early warning they serve as the baseline.',
        items: [
          { title: 'WHO situation reports', body: 'Weekly detail on active outbreaks. Country tables of cases, deaths and CFR are machine-read into signals.', meta: 'Weekly' },
          { title: 'WHO Disease Outbreak News', body: 'Notices for newly confirmed outbreaks.', meta: 'Irregular' },
          { title: 'Africa CDC', body: 'Outbreak status across the African region.', meta: 'Weekly' },
          { title: 'CDC travel health notices', body: 'US CDC country-level travel notice levels.', meta: 'As issued' },
          { title: 'WAHIS (animal disease)', body: 'The animal-stage signal for zoonotic disease.', meta: 'As issued' },
          { title: 'KDCA (Korea)', body: 'Korean notifiable disease weekly statistics.', meta: 'Weekly' },
        ],
      },
      {
        title: 'News & media',
        body: 'Faster than official reporting and much noisier. Weighted low and always cross-checked against another axis.',
        items: [
          { title: 'Local-language news', body: '179 countries. Reporting before international media picks an event up.', meta: 'Hourly' },
          { title: 'GDELT news coverage', body: 'Global news volume trends — we watch surges in attention, not individual articles.', meta: 'Daily' },
          { title: 'Search & social attention', body: 'Public interest indicators such as encyclopedia pageviews.', meta: 'Daily' },
        ],
        note: 'News only moves after a journalist has already written the story, which makes it a lagging indicator and never a primary source.',
      },
      {
        title: 'Environmental & indirect',
        body: 'These watch the conditions for an outbreak and the preparations around it. Not direct evidence, but they can move while every other axis is quiet.',
        items: [
          { title: 'Climate signals', body: 'Conditions for vector-borne spread (temperature, rainfall).', meta: 'Daily' },
          { title: 'Satellite forest change', body: 'Habitat destruction is linked to zoonotic spillover risk.', meta: 'Weekly' },
          { title: 'Trade statistics', body: 'A surge in protective equipment imports proxies preparation behaviour.', meta: 'Monthly · ~2 month reporting lag' },
          { title: 'Wastewater surveillance', body: 'Pathogen detection ahead of symptom onset.', meta: 'Weekly' },
          { title: 'Air mobility', body: 'Used to estimate importation pathways.', meta: 'Real time' },
          { title: 'Supply chain signals', body: 'Availability shifts in antipyretics, masks and similar.', meta: 'Weekly' },
        ],
        note: 'Air mobility is currently blocked from our cloud servers and is not being received. We state that rather than hide it.',
      },
      {
        title: 'Research & genomic',
        items: [
          { title: 'medRxiv · bioRxiv', body: 'Preprints ahead of peer review, where a signal can surface before official announcement.', meta: 'Daily' },
          { title: 'Genomic sequence analysis', body: 'Variant characterisation and sequence naturalness assessment.', meta: 'On request' },
          { title: 'Brazil InfoDengue', body: 'City-level weekly dengue counts.', meta: 'Weekly' },
        ],
      },
    ],
    cta: {
      title: 'Check whether they are alive right now',
      body: 'The dashboard shows the recent collection state of every source.',
      label: 'Open the live dashboard',
      href: '/dashboard',
    },
  },

  methodology: {
    metaTitle: 'Methodology — four layers',
    metaDescription:
      'AEGIRON’s methodology across collection, extraction, analysis and forecasting layers — established academic methods packaged as a commercial product.',
    eyebrow: 'METHODOLOGY',
    title: 'Four layers',
    lead: 'We did not invent new mathematics. We took methods already established in infectious disease epidemiology and surveillance epidemiology and wrapped them in a product that runs itself every day. Here is which standard each layer follows.',
    blocks: [
      {
        title: 'Layer 1 · Collection',
        body: 'Twenty-one heterogeneous sources are normalised into one signal format. Trust differs by source, so it is stored alongside the value and used as a weight in every later calculation.',
      },
      {
        title: 'Layer 2 · Extraction',
        body: 'Structured figures are pulled out of unstructured documents — PDF tables and article text. Page images are interpreted block by block, and extracted numbers are cross-checked against the raw text. Anything not confirmed there is marked unverified.',
      },
      {
        title: 'Layer 3 · Analysis',
        body: 'This layer follows surveillance epidemiology conventions. Anomaly detection uses country-baseline z-scores and CDC EARS-family methods; performance is expressed as sensitivity, specificity, positive predictive value and false alarm rate.',
        points: [
          'Sensitivity (POD) = the share of real outbreaks caught',
          'Specificity = the share of ordinary periods correctly left alone',
          'False alarm rate (FAR) = the share of alerts that were not real',
          'The right false alarm rate is **operating policy, not engineering** — how many alerts a team can review daily, and how much worse a miss is than a false alarm, is an organisational decision. So we do not pick a threshold; we show the whole operating characteristic curve.',
        ],
      },
      {
        title: 'Layer 4 · Forecasting',
        body: 'A standard SEIR compartmental model with time-varying interventions estimates the trajectory. Disease parameters come from measured values in the literature.',
        points: [
          'Contact-limited pathogens have their **reachable population** capped. Applying Ebola’s R0 of 1.8 to an entire population produces 87 times the largest outbreak in history — it actually did, and we fixed it.',
          'Intervention effect is judged by whether the effective reproduction number falls below one.',
          'Every result is labelled a model scenario and carries its historical comparison alongside.',
        ],
      },
      {
        title: 'Where this sits',
        body: 'Combining forecasting with simulation in epidemic modelling is territory Imperial College MRC GIDA, Northeastern’s MOBS Lab and others have worked in for over a decade. What AEGIRON built is not the method but **the structure that runs those methods automatically, every day, as a commercial product.** We do not claim a world first.',
      },
    ],
  },

  solutionsReinsurance: {
    metaTitle: 'For reinsurance & insurance',
    metaDescription:
      'Country exposure indices and portfolio comparison — always stated as relative indices, never absolute probabilities.',
    eyebrow: 'FOR REINSURANCE',
    title: 'Reinsurance & insurance',
    lead: 'The seat for quantifying pandemic risk is currently empty. What we produce, though, is a relative index rather than a probability — and the response makes that distinction explicit rather than leaving it to the reader.',
    blocks: [
      {
        title: 'What you get',
        items: [
          { title: 'Country exposure index', body: 'A 0–100 index synthesising signal pressure, vulnerability and spread potential, built for comparison and ranking.' },
          { title: 'Portfolio comparison', body: 'Your held countries in one view, ranked by relative percentile.' },
          { title: 'Intervention counterfactual', body: 'The modelled difference between no action and intervention scenarios.' },
          { title: 'Sealed forecast record', body: 'Forecasts are sealed at creation, so a verifiable record accumulates on its own as time passes.' },
        ],
      },
      {
        title: 'What you must know',
        accent: true,
        points: [
          'The exposure index is **not an absolute probability.** Every response carries `is_probability: false`.',
          'The weights are policy choices, not empirically calibrated values. `weights_calibrated: false` is stated explicitly.',
          'There is no validated forecast record yet. This is not at a stage to feed rate-setting directly.',
        ],
      },
    ],
    cta: {
      title: 'Start with due diligence',
      body: 'The whole system is open, so check it first and talk to us afterwards.',
      label: 'Get in touch',
      href: 'contact',
    },
  },

  solutionsGovernment: {
    metaTitle: 'For government & public health',
    metaDescription:
      'Importation pathway tracing and intervention comparison, with the modelled effect of each control measure.',
    eyebrow: 'FOR GOVERNMENT',
    title: 'Government & public health',
    lead: 'Two questions together: how an outbreak abroad reaches your population, and which measures actually bring transmission under control.',
    blocks: [
      {
        title: 'What you get',
        items: [
          { title: 'Importation pathway tracing', body: 'Risk pathways estimated from air connectivity and city-level weighting.' },
          { title: 'Intervention comparison', body: 'Combinations of isolation, distancing, vaccination and treatment, searching for the minimum set that drives the effective reproduction number below one.' },
          { title: 'Hospital burden estimate', body: 'Days of bed capacity overflow estimated from the epidemic curve.' },
          { title: 'Daily briefing', body: 'An automatically generated situation summary. On quiet days it says so.' },
        ],
      },
      {
        title: 'What you must know',
        accent: true,
        points: [
          'Scenario figures are **estimates under model assumptions.** Epidemiological review is required before they inform policy.',
          'Where a value falls outside what history can explain, the system attaches its own warning.',
        ],
      },
    ],
    cta: {
      title: 'Open it first',
      body: 'Everything needed for an evaluation is already public.',
      label: 'Get in touch',
      href: 'contact',
    },
  },

  solutionsNgo: {
    metaTitle: 'For multilateral & humanitarian organisations',
    metaDescription:
      'Early signals from places with weak surveillance — including countries others skip because they are commercially unattractive.',
    eyebrow: 'FOR MULTILATERAL & HUMANITARIAN',
    title: 'Multilateral & humanitarian',
    lead: 'The weaker the surveillance, the later the signal. Those regions are commercially unattractive, so few others cover them — which is exactly why we do.',
    blocks: [
      {
        title: 'What you get',
        items: [
          { title: 'Priority on underserved regions', body: 'Nigeria, Ethiopia, Yemen, Madagascar, Papua New Guinea and other countries with large surveillance gaps.' },
          { title: 'First local reporting', body: 'Local coverage from before international media engage.' },
          { title: 'Unexplained event detection', body: 'Clusters not explained by any known disease are flagged separately.' },
          { title: 'Gap reporting', body: 'The system reports which regions and periods are empty — which is itself operationally useful information.' },
        ],
      },
      {
        title: 'What you must know',
        accent: true,
        points: [
          'The weaker a region’s surveillance, the **more likely our own data is empty there too.** Gaps are shown, not hidden.',
          'Local-language handling is keyword-based rather than machine-translated, because machine translation failed our quality check.',
        ],
      },
    ],
    cta: {
      title: 'We are looking for field partners',
      body: 'Connecting with organisations close to real field signals is the single most valuable next step for us.',
      label: 'Get in touch',
      href: 'contact',
    },
  },

  briefings: {
    metaTitle: 'Daily briefings',
    metaDescription:
      'AEGIRON’s automatically generated daily infectious disease briefing. On quiet days it says so.',
    eyebrow: 'BRIEFINGS',
    title: 'Daily briefings',
    lead: 'Generated automatically every day. Because no human edits them, a day with nothing in it reads as a day with nothing in it.',
    blocks: [
      {
        title: 'How they are made',
        body: 'The day’s collected signals and country risk scores are assembled into a summary. The format rotates — breaking desk, deep dive, field report, data briefing, anchor conversation. Every figure in a briefing is a value the system actually received that day.',
        note: 'A briefing is a summary, not a forecast. If you need a judgement on a particular country, check the underlying evidence on the dashboard.',
      },
    ],
    cta: {
      title: 'See what the system is looking at today',
      body: 'The dashboard shows the signals a briefing was built from.',
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
          'No external body has independently validated us. So far, the only people who have evaluated this system are the people who built it.',
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
    lead: 'You can see the entire system without booking a demo. If questions come up once you have, that is a good time to write.',
    blocks: [
      {
        title: 'How to reach us',
        items: [
          { title: 'Email', body: 'kimdaeheuk@gmail.com', meta: 'The fastest route' },
          { title: 'Location', body: 'Busan, South Korea', meta: 'KST (UTC+9)' },
        ],
      },
      {
        title: 'Especially welcome',
        points: [
          '**Corrections** — if the methodology or a figure is wrong, tell us. It gets fixed.',
          '**Field connections** — a route to real surveillance networks is what we need most right now.',
          '**Pilot discussions** — reinsurance, government or multilateral.',
        ],
      },
    ],
  },

  privacy: {
    metaTitle: 'Privacy policy',
    metaDescription: 'How the AEGIRON website handles personal data.',
    eyebrow: 'LEGAL',
    title: 'Privacy policy',
    lead: 'This site does not ask visitors to log in and does not collect personal data.',
    blocks: [
      {
        title: 'What we do not collect',
        points: [
          'There is no signup or login, so no account data is collected.',
          'This site does not use advertising trackers.',
          'Viewing the dashboard requires no personally identifying information.',
        ],
      },
      {
        title: 'If you write to us',
        body: 'Email you send is used only to reply and is not shared with third parties.',
      },
      {
        title: 'Changes',
        body: 'If this policy changes, this page is updated.',
      },
    ],
  },

  terms: {
    metaTitle: 'Terms of use',
    metaDescription: 'Conditions for using the AEGIRON website and public data.',
    eyebrow: 'LEGAL',
    title: 'Terms of use',
    lead: 'These conditions apply to this site and the public dashboard.',
    blocks: [
      {
        title: 'The nature of what is provided',
        accent: true,
        points: [
          'Information here is **for reference** and is not provided as a basis for medical, public health or investment decisions.',
          'Forecast and scenario figures are **estimates under model assumptions** — neither measurements nor guarantees.',
          'AEGIRON does not yet hold a validated track record for early-detection accuracy.',
          'We accept no liability for outcomes of decisions made on the basis of this information.',
        ],
      },
      {
        title: 'Data provenance',
        body: 'This system collects and processes public material from WHO, CDC and others. Copyright and terms for the original material rest with those bodies. Processed figures may differ from the originals, so for any formal citation please verify against the originating source.',
      },
      {
        title: 'Availability',
        body: 'The public dashboard may be interrupted or changed without notice.',
      },
    ],
  },
};
