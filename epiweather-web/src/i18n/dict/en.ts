import type { Dictionary } from '../types';

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
    methodology: 'Methodology',
    transparency: 'What we don’t know',
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
    metaTitle: 'AEGIRON — Infectious disease early warning, shown as it actually runs',
    metaDescription:
      'An early-warning system monitoring 21 live data sources for infectious disease signals. The live dashboard, the full methodology and every data source are open without a login — and so are the things we have not yet validated.',

    heroEyebrow: 'Fully open · No login',
    heroTitle: 'See the system\nexactly as it runs today',
    heroLead:
      'Most infectious disease intelligence sits behind a sales call. AEGIRON publishes the live system, the methodology, every data source, and the parts we have not yet validated. Look first, then judge.',
    heroPrimaryCta: 'Open the live dashboard',
    heroSecondaryCta: 'See how it works',
    heroNoLogin: 'Opens immediately — no signup, no login',

    stats: [
      { value: '21', label: 'Live data sources', note: 'WHO · CDC · local-language news · climate · satellite' },
      { value: '106', label: 'API endpoints', note: 'Collection · analysis · forecasting · simulation' },
      { value: '217', label: 'Country reference set', note: 'Vulnerability index built on World Bank data' },
      { value: '740', label: 'Automated tests', note: 'All passing · re-run on every change' },
    ],

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
