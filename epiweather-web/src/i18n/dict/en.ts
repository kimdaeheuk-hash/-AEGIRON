import type { Dictionary } from '../types';
import { pagesEn } from './pages.en';
import { extraEn } from './extra.en';

/**
 * English dictionary — the language our primary buyers actually read
 * (Munich Re, Marsh, Swiss Re, WHO, MSF).
 *
 * ★ HARD RULE ★ No accuracy or lead-time claims.
 * "Detected N days earlier", "N% accurate", "N outbreaks predicted" are all
 * forbidden — we have no validated track record and a reinsurer's due diligence
 * would surface that immediately. Only measurable facts: infrastructure scale,
 * what we publish, and what we do not yet know.
 */
export const en: Dictionary = {
  pages: pagesEn,
  extra: extraEn,

  briefings: {
    archiveTitle: 'Past briefings',
    count: '{n} briefings',
    quietDay: 'Quiet day',
    openBrief: 'Read',
    empty: 'No briefings have been archived yet.',
    error: 'The briefings could not be loaded. The system itself is still running.',
    backToList: 'All briefings',
    summary: 'Summary',
    segments: 'Sections',
    ticker: 'Ticker',
    disclosure: 'Disclosure',
    notFound: 'There is no briefing for that date.',
    langNoticeTitle: 'A note on language',
    langNoticeMismatch:
      'This briefing was generated in a different language from the one requested. We show it as-is rather than hiding the mismatch.',
  },

  common: {
    siteName: 'AEGIRON',
    siteTagline: 'Infectious disease early-warning intelligence',
    readMore: 'Read more',
    backToHome: 'Back to home',
    lastUpdated: 'Last updated',
    liveNow: 'Live',
  },

  nav: {
    live: 'Live operations',
    baikal: 'BAIKAL MOB',
    record: 'Public forecast ledger',
    korea: 'For Korea',
    security: 'Security & governance',
    press: 'Media kit',
    pilot: 'How to engage',
    developers: 'Developers · API',
    diseases: 'Disease watch',
    solNgo: 'International & humanitarian',
    solReinsurance: 'Reinsurance & insurance',
    solGovernment: 'Government & public health',
    engines: 'Engine catalogue',
    techSpec2: 'Tech Spec II · Analysis & response',
    techSpec1: 'Tech Spec I · Surveillance & ingestion',
    trust: 'Evidence & data',
    company: 'Company',
    platform: 'Platform',
    technology: 'Technology',
    programs: 'Special programs',
    methodology: 'Methodology',
    transparency: 'Validation framework',
    dataSources: 'Data sources',
    solutions: 'Use cases',
    briefings: 'Daily briefings',
    about: 'About AEGIRON',
    contact: 'Contact',
    dashboard: 'Live dashboard',
    openMenu: 'Open menu',
    closeMenu: 'Close menu',
    language: 'Language',
  },

  footer: {
    tagline: 'Before an outbreak becomes international news.',
    product: 'Product',
    company: 'Company',
    legal: 'Legal',
    privacy: 'Privacy policy',
    terms: 'Terms of use',
    rights: 'All rights reserved.',
    location: 'Busan, South Korea',
    disclaimer:
      'AEGIRON does not yet hold a validated track record for early-detection accuracy. Every figure on this site measures the scale of the system, not its predictive performance.',
  },

  home: {
    metaTitle: 'AEGIRON — Infectious disease early warning, forecasting and spread simulation',
    metaDescription:
      'An infectious disease intelligence system that detects anomalies in local-language reporting from 179 countries and in official surveillance data, attaches intervention scenarios to every alert, and scores each of its forecasts against the official declarations that follow.',

    heroLiveOk: 'Data sources: {ok}/{total} reporting normally',
    heroLiveUnknown: 'Collection status could not be checked just now',
    heroTitle: 'Beyond alerts —\n[[forecasting]] and [[simulation]]',
    heroLead:
      'AEGIRON detects anomalies in local-language reporting from 179 countries and in official surveillance data, and the moment an alert is raised it computes spread scenarios for each level of intervention. Every forecast is scored automatically against the official declarations that follow; a forecast with nothing to score it against is counted neither as a hit nor as a miss.',
    heroPrimaryCta: 'Live dashboard',
    heroSecondaryCta: 'Engine architecture',
    heroNoLogin: 'Opens immediately — no signup, no login',

    stats: [
      { value: '118', label: 'Algorithm modules', note: '116 engines · 2 for the ontology (YGGDRASIL) and state layer (BAIKAL MOB)' },
      { value: '128', label: 'API endpoints', note: 'Collection · analysis · simulation · scoring' },
      { value: '2,263', label: 'Automated tests', note: 'All must pass before anything reaches production' },
      { value: '179', label: 'Local-language news feeds', note: 'Aggregated by country and language, collected hourly' },
    ],
    statsAsOf: 'Measured 2026-10-19 from the repository and production logs',
    introVideoLabel: 'AEGIRON — introduction',
    photo: {
      src: '/media/photos/earth-eastern-hemisphere.jpg',
      alt: 'Earth’s Eastern Hemisphere — Africa, Europe and Asia (satellite composite)',
      caption: 'Earth’s Eastern Hemisphere (Blue Marble). A composite of satellite observations.',
      credit: 'NASA · Public domain',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:Blue_Marble_Eastern_Hemisphere.jpg',
      position: 'center 45%',
    },

    galleryTitle: 'Where the signals arise',
    galleryLead:
      'The world AEGIRON watches is outside the lab, not inside it. Laboratories, field response, the international air network, wastewater, hospital beds — the places where an outbreak signal actually arises. Every image below is public material (public-domain or free licence) and shows what we watch, not an AEGIRON facility.',
    gallery: [
      {
        src: '/media/photos/emergency-operations-center.jpg',
        alt: 'Inside an emergency operations centre with many screens',
        caption: 'An emergency operations centre — where an alert reaches people and turns into response.',
        credit: 'Office of the President, ROC · CC BY 2.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:Central_Emergency_Operation_Center_2024-10-31.jpg',
      },
      {
        src: '/media/photos/ebola-field-response.jpg',
        alt: 'Health workers in protective gear during an Ebola response',
        caption: 'Ebola response in the field (West Africa, 2014). Before local reporting is translated, the signal arises first in places like this.',
        credit: 'Sgt. 1st Class Nathan Hoskins, U.S. Army · Public domain',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:United_Assistance_141105-A-CH600-043.jpg',
      },
      {
        src: '/media/photos/world-air-routes.jpg',
        alt: 'A world map of global airline routes',
        caption: 'The international air network — the real shape of the 1,671 country pairs the spread digital twin links across 159 countries.',
        credit: 'aomd88 · CC BY 1.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:EK_emirates_2011_routes_world_map.jpg',
      },
      {
        src: '/media/photos/dna-sequencer.jpg',
        alt: 'A genome sequencing instrument',
        caption: 'A genome sequencer. The signal of a variant shows in the sequence before it shows in case counts.',
        credit: 'Scotted400 · CC BY 4.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:Revolocity_DNA_sequencer.jpg',
      },
      {
        src: '/media/photos/wastewater-plant.jpg',
        alt: 'Aerial view of a wastewater treatment plant',
        caption: 'A wastewater treatment plant. Wastewater surveillance catches a pathogen signal from before symptoms appear.',
        credit: 'Sdkb · CC BY-SA 4.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:Blue_Plains_Advanced_Wastewater_Treatment_Plant_aerial_view,_2025.jpg',
      },
      {
        src: '/media/photos/sars-cov-2-niaid.jpg',
        alt: 'Electron micrograph of SARS-CoV-2 virus particles (colorized)',
        caption: 'SARS-CoV-2 virus particles (colorized). Public material from the US NIAID.',
        credit: 'NIAID · CC BY 2.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:Novel_Coronavirus_SARS-CoV-2_(49597020648).jpg',
      },
      {
        src: '/media/photos/hospital-icu.jpg',
        alt: 'An intensive care unit bed',
        caption: 'An intensive-care bed. The “days of hospital overload” the intervention scenarios estimate land here.',
        credit: 'Ismael Olea · CC BY 4.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:20250808_Intensive_care_unit_bed.jpg',
      },
      {
        src: '/media/photos/data-center.jpg',
        alt: 'A data-centre server room',
        caption: 'A data centre. The hourly computation of 118 modules runs in places like this.',
        credit: 'BalticServers.com · CC BY-SA 3.0',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:BalticServers_data_center.jpg',
      },
      {
        src: '/media/photos/arctic-permafrost.jpg',
        alt: 'Arctic thaw ponds formed by melting permafrost',
        caption: 'Permafrost thaw (Arctic). The new outbreak conditions polar-territory surveillance watches.',
        credit: 'NPS Climate Change Response · Public domain',
        sourceUrl: 'https://commons.wikimedia.org/wiki/File:Permafrost_Thaw_(14413865677).jpg',
      },
    ],

    engineTitle: 'The seven engine systems',
    engineLead:
      'The {n} core engines out of 116 modules, organised into the seven systems (HUGINN · MIMIR · FORSETI · SKULD · HEIMDALL · VALHALLA · VAR). Each one is labelled with how it actually runs, so that an engine that runs every hour is never presented with the same weight as one that computes only when asked.',
    engineModes: {
      hourly: 'Runs hourly',
      daily: 'Runs daily',
      onAlert: 'Runs on alert',
      onRequest: 'On request',
    },
    engineCaveatLabel: 'Limits',
    engineGroups: [
      {
        system: 'HUGINN',
        engines: [
          {
            id: 'local_news',
            name: 'Local-language news surveillance',
            body: 'Measures the density of disease vocabulary in news aggregated by country and language, and re-classifies ambiguous feeds with a language model. The target is the first local report, before any English-language coverage exists.',
            mode: 'hourly',
          },
          {
            id: 'gai',
            name: 'Six-layer anomaly index',
            body: 'Converts signals from six layers — official, unofficial, behavioural, environmental, animal and unexplained — into anomaly scores against each signal’s own baseline, weights them by source reliability and combines them into one index. The reference is each indicator’s usual level, not its absolute volume.',
            mode: 'hourly',
          },
          {
            id: 'negative_space',
            name: 'Reporting-silence watch',
            body: 'Tracks reporting channels that fall below half their baseline. It targets cases such as Ebola in Guinea in 2014, where the collapse of reporting came before the spread, and judges only indicators with a declared decision rule.',
            mode: 'hourly',
          },
          {
            id: 'unexplained',
            name: 'Unexplained clusters',
            body: 'Counts, as a separate class, clusters extracted from reporting that do not match any known disease pattern. The pneumonia of unknown cause in Wuhan in December 2019 is the archetype.',
            mode: 'hourly',
          },
          {
            id: 'polar_signals',
            name: 'Polar-territory surveillance',
            body: 'Observes the Arctic, the Antarctic and 27 glacier mountain regions with baseline and trend. As permafrost thaws — exposing pathogens and polar avian influenza — it watches, at the territory level, the new outbreak conditions a changing climate opens.',
            mode: 'daily',
            caveat: 'An object of observation, not an alert. A polar signal does not by itself mean an outbreak.',
          },
          {
            id: 'disaster_watch',
            name: 'Disaster watch window',
            body: 'After floods, quakes and storms, the country is watched at a lower threshold through the window when water- and vector-borne risk rises. It targets the time between a disaster and the outbreak that follows.',
            mode: 'hourly',
          },
          {
            id: 'comtrade_signals',
            name: 'Medical-supply trade watch',
            body: 'Detects import surges of masks, PPE and test kits by country via UN Comtrade — a preparedness-behaviour signal that can appear before an official announcement.',
            mode: 'daily',
            caveat: 'Trade filings lag by roughly two months and are not a real-time indicator.',
          },
        ],
      },
      {
        system: 'MIMIR',
        engines: [
          {
            id: 'nlp_extract',
            name: 'Structured signal extraction',
            body: 'Turns article text into structured signals — disease, country, cases, deaths and signal type — assigns source reliability, and keeps unconfirmed values apart as unverified.',
            mode: 'daily',
            caveat: 'Runs once a day in the AI slot (21:00 UTC), currently through an external language-model path.',
          },
          {
            id: 'pdf_table_extract',
            name: 'WHO report table extraction',
            body: 'Rebuilds the PDF tables of WHO regional weekly situation reports into rows and columns, and counts “new in 7 days”, “cumulative”, “suspected” and “confirmed” separately.',
            mode: 'daily',
            caveat: 'Parses only when a new issue exists — the reports are published weekly.',
          },
        ],
      },
      {
        system: 'FORSETI',
        engines: [
          {
            id: 'country_risk',
            name: 'Country risk index',
            body: 'Multiplies raw (signal-based) risk by national vulnerability — health infrastructure, population density, airport connectivity — to give each country’s final risk, and records it as a forecast once it crosses the threshold.',
            mode: 'hourly',
            caveat: 'A relative indicator between countries, not a probability of occurrence.',
          },
          {
            id: 'alerts',
            name: 'Alert triage and fatigue control',
            body: 'Applies tiers (Critical · High · Medium · Low) and per-tier daily caps so that only alerts worth a person’s attention go out. Critical and High go to Telegram at once; families that could not be assessed are held with a staleness mark rather than withdrawn.',
            mode: 'hourly',
          },
        ],
      },
      {
        system: 'SKULD',
        engines: [
          {
            id: 'forecast_engine',
            name: '7- and 14-day trend outlook',
            body: 'Extrapolates each indicator’s time series 7 and 14 days ahead with an ensemble of linear regression and exponential smoothing, and publishes the result in the daily briefing.',
            mode: 'daily',
            caveat: 'An extrapolation of signal time series, not a measured case count.',
          },
          {
            id: 'digital_twin',
            name: 'Cross-border spread simulation',
            body: 'A metapopulation SEIR model with 159 countries as nodes and 1,671 air-linked country pairs and 314 land borders as edges. It reports countries not reached within the period separately from countries for which no route is known.',
            mode: 'onRequest',
            caveat: 'The air network uses 2014 route data; land traffic is a population-based estimate.',
          },
          {
            id: 'global_inflow',
            name: 'Import-date estimate',
            body: 'Estimates the days until a first imported case reaches Korea, and the risk at each port of entry, from the origin city’s international passenger volume, flight time and early exponential growth.',
            mode: 'onRequest',
            caveat: 'A model estimate, not an observed import date.',
          },
          {
            id: 'alert_intervention',
            name: 'Intervention scenarios per alert',
            body: 'For every new critical or high alert, runs an SEIR defence simulation with disease-specific parameters and attaches the difference between no response and intervention. The alert no longer stops at “what is coming”; it also answers “which measures change what”.',
            mode: 'onAlert',
            caveat: 'A model scenario built on literature parameters, not a forecast. No figures are produced for alerts where the disease cannot be identified.',
          },
          {
            id: 'defense',
            name: 'Time-varying intervention comparison',
            body: 'Varies the start date and intensity of isolation, distancing and vaccination to compare how the effective reproduction number and days of hospital overload change.',
            mode: 'onRequest',
          },
        ],
      },
      {
        system: 'HEIMDALL',
        engines: [
          {
            id: 'genomic_variants',
            name: 'Clade composition tracking',
            body: 'Reads shifts in dominant-clade share and the emergence of new clades from Nextstrain’s reanalysis of public sequences — changes in transmissibility or immune escape that move before case counts do. Builds that have stopped updating are not used as signals.',
            mode: 'hourly',
          },
          {
            id: 'evo2_naturalness',
            name: 'Measured sequence-order naturalness',
            body: 'Gives the genomic foundation model Evo2 only the first part of a sequence, asks it to predict the next bases, and measures agreement with the real sequence. It targets spliced or recombined segments that composition statistics cannot reveal.',
            mode: 'onRequest',
            caveat: 'Evo2 excluded eukaryotic-host viruses from training, so it is not applied to coronavirus, influenza or Ebola sequences.',
          },
          {
            id: 'msa_homology',
            name: 'Homology-based chimera detection',
            body: 'Searches public homology databases to see whether any natural protein covers the full length of the query. Because it is a search rather than a trained model, it also works for pathogens Evo2 cannot handle.',
            mode: 'onRequest',
          },
        ],
      },
      {
        system: 'VALHALLA',
        engines: [
          {
            id: 'valhalla_watch',
            name: 'Countermeasure readiness watch',
            body: 'Compiles international stockpiles, approved products, WHO prequalification, the clinical pipeline and Korean procurement notices into per-threat coverage and manufacturing-sovereignty gaps.',
            mode: 'hourly',
            caveat: 'Procurement and clinical parts refresh on their own cadences; non-public information such as national stockpile volumes is not handled.',
          },
        ],
      },
      {
        system: 'VAR',
        engines: [
          {
            id: 'prediction_resolver',
            name: 'Automatic forecast scoring',
            body: 'Checks recorded forecasts every day against the official declarations that follow and sorts them into hit, miss or undetermined. Spikes in page views and case-count updates are never used as ground truth — that would be scoring our signals with our own signals.',
            mode: 'daily',
          },
          {
            id: 'lead_time_ledger',
            name: 'Lead-time ledger',
            body: 'Records the moment a signal was first seen before any official declaration. A lead time found by searching backwards after a declaration is not accepted as a measurement.',
            mode: 'hourly',
          },
          {
            id: 'prediction_timestamp',
            name: 'Forecast sealing',
            body: 'Anchors the SHA-256 hash of a forecast record in the Bitcoin blockchain through OpenTimestamps, so that a third party can verify for themselves that the forecast was not rewritten after the fact.',
            mode: 'hourly',
          },
          {
            id: 'source_health',
            name: 'Silent-failure watch',
            body: 'Counts separately, every cycle, whether each source actually delivered values and whether the method that produced them still holds. A source whose collection ran but returned nothing is not counted as healthy.',
            mode: 'hourly',
          },
        ],
      },
    ],

    engineCatalogueCta: 'See the role of all 116 modules in the engine catalogue',

    diffEyebrow: 'WHAT MAKES US DIFFERENT',
    diffTitle: 'What sets us apart from other early warning',
    diffLead:
      'Early warning for infectious disease is not new — services like BlueDot, EIOS and Metabiota already exist. Where AEGIRON differs is that it does not stop at detection but puts verification, response and sovereignty into one system. We state this by structure, without overstatement.',
    diffItems: [
      {
        title: 'It does not stop at detection',
        body: 'Most early warning stops at “something is happening, somewhere”. AEGIRON attaches spread simulation, intervention scenarios and countermeasure readiness, to answer “so what, and at what strength”.',
      },
      {
        title: 'It scores its own numbers',
        body: 'Every forecast is sealed when made and checked daily against official declarations, recording hit and miss by itself. Building a track record as a verifiable record rather than a claim is rare.',
      },
      {
        title: 'Surveillance gaps included from the start',
        body: 'It watches, to the same standard, 178 countries and 52 languages that commercial services rarely cover — Africa, Central Asia, Pacific island states, and polar territory too.',
      },
      {
        title: 'A national-biosecurity axis',
        body: 'Defensive genomic screening (HEIMDALL) and countermeasure coverage / production-sovereignty analysis (VALHALLA) are a national-scale axis that commercial early-warning services do not have.',
      },
      {
        title: 'Everything open',
        body: 'The system, methodology, data and limits are open from the start — something a larger service bound by customer contracts would find hard to follow, and a basis for trust that due diligence can verify directly.',
      },
    ],
    futureTitle: 'Where we are headed',
    futureLead: 'This is a starting point. It is built to grow stronger as operation accrues.',
    futureItems: [
      {
        title: 'A proprietary extraction model',
        body: 'Extraction runs through external APIs today, but the path is wired so it can switch, in one place, to a self-hosted model (NVIDIA NIM), moving toward a design where sensitive data does not leave for overseas APIs.',
      },
      {
        title: 'A data moat',
        body: '“Which signal led to a real outbreak” is assembled into a training set every day. As operation continues, that set grows and heuristics can be replaced by a measured learning model.',
      },
      {
        title: 'A sealed track record',
        body: 'As sealed forecasts accumulate, “we knew first” becomes a record a third party can verify on the blockchain — the verifiable record grows with time.',
      },
      {
        title: 'Field connections',
        body: 'The next step is connecting with real surveillance networks and field organisations to get closer to the source of the signal — the path to becoming global early-warning infrastructure.',
      },
    ],

    specialEyebrow: 'SPECIAL PROGRAMS',
    specialTitle: 'Two axes no competitor has — HEIMDALL · VALHALLA',
    specialLead: 'Most surveillance layers run in the open. But two internal R&D programs, different in kind, carry the national-biosecurity axis. We state only what they do and do not do, without overstating any of it.',
    specialCards: [
      { code: 'HEIMDALL', name: 'Defensive genomic screening', body: 'Detects and flags whether a sequence departs from the statistics of natural evolution. No design or synthesis function — a review priority, not a verdict.' },
      { code: 'VALHALLA', name: 'Countermeasure readiness', body: 'Instead of imitating molecular prediction, it aggregates stockpile-coverage and production-sovereignty gaps from public data. It does not touch non-public information such as national stockpile quantities.' },
    ],
    specialCta: 'See the special programs',

    openTitle: 'Open, so it can be checked',
    openLead:
      'The most common failure in disease surveillance is not a wrong forecast but one nobody can check. So the system, the methodology, the data and the limits behind every judgement are open from the start.',
    openItems: [
      {
        title: 'The live system',
        body: 'The dashboard shows operational collection and alert data as it runs. In the simulation console, assumed and modelled values are labelled as such on screen.',
        href: '/dashboard',
        linkLabel: 'Open the dashboard',
      },
      {
        title: 'Methodology',
        body: 'How signals are collected, how anomalies are judged and how forecasts are made, set out in four layers — with the standard each layer follows.',
        href: '/methodology',
        linkLabel: 'Read the methodology',
      },
      {
        title: 'Data sources',
        body: 'Every operational source, listed without exception, with what each one cannot see and whether it is healthy right now.',
        href: '/data-sources',
        linkLabel: 'See the sources',
      },
      {
        title: 'Validation and limits',
        body: 'What has not yet been validated, the known limits and data gaps, and how the system checks its own numbers.',
        href: '/transparency',
        linkLabel: 'See validation status',
      },
    ],

    honestTitle: 'We check our own numbers first',
    honestLead:
      'Trust in an early-warning system comes from its verification path, not from the size of its claims. Here is what we do not yet have — and the mechanisms already running to close that gap.',
    honestPoints: [
      'There is **no validated track record yet** for early-detection accuracy. That is why we make no “detected days earlier” claims.',
      'Instead, every forecast is **sealed at the moment it is made** and scored daily against the official declarations that follow. The track record accrues from this record, not from assertion.',
      'Scenario figures are labelled as **model estimates under stated assumptions**, and are checked automatically against the largest outbreaks on record — a warning travels with any value outside that range.',
      'Data gaps are never hidden. The system reports which countries and periods are empty, and which sources have stopped.',
    ],
    honestClose:
      'When an outbreak is missed, we report “the model missed it” separately from “there was no data to see it”. Mixing the two turns the diagnosis upside down.',
    honestCta: 'See the full validation status',

    pipelineTitle: 'From signal to alert',
    pipelineLead: 'Five stages. At each one, what we leave out matters as much as what we use.',
    pipelineSteps: [
      {
        step: '01',
        title: 'Collect',
        body: 'Official data from WHO regional offices and national health authorities, local-language reporting from 179 countries, academic sources, wastewater surveillance and genomic lineage data — every hour.',
      },
      {
        step: '02',
        title: 'Extract',
        body: 'Disease, country, cases and deaths are structured from PDF tables and article text. Anything that cannot be read is left empty, never filled by guesswork.',
      },
      {
        step: '03',
        title: 'Judge',
        body: 'Anomalies are measured against each indicator’s usual level, not in absolute terms — the same five cases mean different things in different countries.',
      },
      {
        step: '04',
        title: 'Forecast',
        body: 'Transmission models estimate spread paths and import risk, and every value carries its assumptions and limits.',
      },
      {
        step: '05',
        title: 'Respond',
        body: 'No-response and intervention scenarios are compared to show which measures, at what intensity, break transmission.',
      },
    ],

    briefTitle: 'Today’s briefing',
    briefLead: 'Generated automatically every day. On quiet days it says so.',
    briefCta: 'Browse past briefings',
    briefEmpty: 'Today’s briefing has not been generated yet.',
    briefError: 'The briefing could not be loaded. The system itself is still running.',

    audienceTitle: 'Who this is for',
    audienceLead: 'The same signal needs a different shape depending on who reads it.',
    audiences: [
      {
        title: 'Reinsurance & insurance',
        body: 'Country exposure indices and portfolio comparison. Every response states explicitly that these are relative indices, not absolute probabilities.',
        href: '/solutions/reinsurance',
      },
      {
        title: 'Government & public health',
        body: 'Importation pathway tracing and intervention comparison, with the modelled effect of each control measure.',
        href: '/solutions/government',
      },
      {
        title: 'Multilateral & humanitarian',
        body: 'Early signals from places with weak surveillance — including countries commercially unattractive enough that others skip them.',
        href: '/solutions/ngo',
      },
    ],

    ctaTitle: 'Everything needed for an evaluation is already open',
    ctaBody:
      'You can review the whole system without booking a demo. For pilots and partnerships, please reach us through the contact page.',
    ctaButton: 'Get in touch',
  },
};
