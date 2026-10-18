import type { Dictionary } from '../types';
import { pagesEn } from './pages.en';

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

  briefings: {
    archiveTitle: 'Past briefings',
    count: '{n} briefings',
    quietDay: 'Quiet day',
    openBrief: 'Read',
    empty: 'No briefings have been archived yet.',
    error: 'The briefings could not be loaded. The system itself is still running.',
    backToList: 'All briefings',
    summary: 'Summary',
    segments: 'Segments',
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
    platform: 'System',
    technology: 'Technology',
    programs: 'Special programs',
    methodology: 'Methodology',
    transparency: 'Validation & limits',
    dataSources: 'Data sources',
    solutions: 'Use cases',
    briefings: 'Briefings',
    about: 'About',
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
      { value: '114', label: 'Algorithm modules', note: 'Detection · genomics · forecasting · response · verification' },
      { value: '123', label: 'API endpoints', note: 'Collection · analysis · simulation · scoring' },
      { value: '2,145', label: 'Automated tests', note: 'All must pass before anything reaches production' },
      { value: '179', label: 'Local-language news feeds', note: 'Aggregated by country and language, collected hourly' },
    ],
    statsAsOf: 'Measured 2026-10-18 from the repository and production logs',
    introVideoLabel: 'AEGIRON — introduction',

    engineTitle: 'The engines',
    engineLead:
      'Sixteen of the 114 modules form the backbone of detection, genomics, forecasting, response and verification. Each one is labelled with how it actually runs, so that an engine that runs every hour is never presented with the same weight as one that computes only when asked.',
    engineModes: {
      hourly: 'Runs hourly',
      daily: 'Runs daily',
      onAlert: 'Runs on alert',
      onRequest: 'On request',
    },
    engineCaveatLabel: 'Limits',
    engineGroups: [
      {
        key: 'detect',
        label: 'Detection',
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
        ],
      },
      {
        key: 'genomics',
        label: 'Genomics',
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
        key: 'simulate',
        label: 'Forecasting · Simulation',
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
        ],
      },
      {
        key: 'respond',
        label: 'Response',
        engines: [
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
        key: 'verify',
        label: 'Self-verification',
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
            mode: 'onRequest',
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

    specialEyebrow: 'SPECIAL PROGRAMS',
    specialTitle: 'Two axes no competitor has — HEIMDALL · VALHALLA',
    specialLead: 'Most surveillance layers run in the open. But two internal R&D programs, different in kind, carry the national-biosecurity axis. We state only what they do and do not do, without overstating any of it.',
    specialCards: [
      { code: 'HEIMDALL', name: 'Defensive genomic screening', body: 'Detects and flags whether a sequence departs from the statistics of natural evolution. No design or synthesis function — a review priority, not a verdict.' },
      { code: 'VALHALLA', name: 'Countermeasure readiness', body: 'Instead of imitating molecular prediction, it aggregates stockpile-coverage and production-sovereignty gaps from public data. It does not touch non-public information such as national stockpile quantities.' },
    ],
    specialCta: 'See the special programs',

    openTitle: 'What we publish',
    openLead:
      'The most common failure in disease surveillance is not a wrong forecast — it is a forecast nobody can check. So we publish everything needed to check ours.',
    openItems: [
      {
        title: 'The live system',
        body: 'The same dashboard we run. Not a demo reel — the operational system currently ingesting signals.',
        href: '/dashboard',
        linkLabel: 'Open dashboard',
      },
      {
        title: 'The full methodology',
        body: 'How signals are gathered, how anomalies are judged, and how forecasts are produced — set out in four layers.',
        href: '/methodology',
        linkLabel: 'Read the methodology',
      },
      {
        title: 'Every data source',
        body: 'All 21 sources listed, with nothing hidden — including which ones are healthy and which are currently blocked.',
        href: '/data-sources',
        linkLabel: 'See the sources',
      },
      {
        title: 'What we don’t know',
        body: 'Unvalidated areas, known limits, and the collection gaps we have not closed. You will not find this page on a competitor’s site.',
        href: '/transparency',
        linkLabel: 'Read the limits',
      },
    ],

    honestTitle: 'What has not been validated',
    honestLead:
      'Few companies put this section on a homepage. But if we do not say it first, due diligence says it for us.',
    honestPoints: [
      'We have **no validated track record** for early-detection accuracy. That is why no claim of the form “detected N days earlier” appears anywhere on this site.',
      'The system entered full operation in 2026. Results for earlier outbreaks are retrospective reconstructions and are not equivalent to live performance.',
      'Scenario figures from the forecasting modules are **estimates under model assumptions** — neither measurements nor guarantees.',
      'There are gaps in our data collection. The system reports which countries and which periods are missing.',
    ],
    honestClose:
      'Here is what we do instead. Model outputs are automatically compared against the largest outbreak on record, and when a number exceeds a defensible range the system **attaches its own warning** before the figure leaves the API. When an outbreak is missed, we separate “the model failed to catch it” from “we had no data to catch it with”.',
    honestCta: 'Read the full list of limits',

    pipelineTitle: 'From signal to alert',
    pipelineLead:
      'Five stages. What each stage discards matters as much as what it keeps.',
    pipelineSteps: [
      {
        step: '01',
        title: 'Collect',
        body: 'WHO situation reports, CDC travel notices, local-language news across 179 countries, climate, satellite and trade statistics.',
      },
      {
        step: '02',
        title: 'Extract',
        body: 'Disease, country, cases and deaths are structured out of PDF tables and article text. Anything unrecognised is left empty rather than guessed.',
      },
      {
        step: '03',
        title: 'Judge',
        body: 'Anomaly is scored against each country’s own baseline, not against an absolute threshold — five signals mean different things in different places.',
      },
      {
        step: '04',
        title: 'Forecast',
        body: 'Transmission models estimate spread and importation risk. Every value carries its assumptions and limits with it.',
      },
      {
        step: '05',
        title: 'Respond',
        body: 'No-action and intervention scenarios are compared, so the output answers “what should be done”, not only “what is coming”.',
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

    ctaTitle: 'Look first. Talk to us after.',
    ctaBody:
      'You can see the entire system without booking a demo. If questions come up once you have, that is a good time to get in touch.',
    ctaButton: 'Get in touch',
  },
};
