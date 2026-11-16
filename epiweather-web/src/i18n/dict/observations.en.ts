import type { ContentPage, ObservationsDict } from '../types';

/** Observation board (English). Measured values and derived values never share a column. */
export const observationsPageEn: ContentPage = {
  metaTitle: 'Observations — what AEGIRON actually measures',
  metaDescription:
    'Polar and permafrost, climate, medical-supply trade, disasters, travel notices and per-country outbreak reports: the measured values AEGIRON pulls in while running, by domain.',
  eyebrow: 'OBSERVATIONS',
  title: 'Observations',
  lead: 'The values AEGIRON actually pulls in while running, by domain · read from the production API · refreshed every few minutes',
  blocks: [],
};

export const observationsEn: ObservationsDict = {
  columns: {
    target: 'Subject',
    measured: 'Measured',
    derived: 'Derived (estimate · proxy)',
    time: 'As of',
    note: 'Note',
  },
  columnsNote:
    'Measured = a value the source observed directly · Derived = an estimate computed from it, or a proxy standing in for something else — the two are never mixed in one column',
  unavailable: 'Could not be read from the production server right now — left blank rather than filled in',
  empty: 'Nothing to show in this domain right now',
  sourceLabel: 'Source',
  countLabel: 'rows',
  caveatKoLabel: 'Original caution note (Korean)',
  globe: {
    title: 'Observation globe',
    lead: 'The values in the tables below, placed on a globe · dot size = records received for that country or region · drag to rotate',
    dragHint: 'Drag to rotate · click a dot for details',
    layers: {
      event: 'Outbreak reports',
      unexplained: 'Unexplained signals',
      disaster: 'Disaster windows',
      trade: 'Medical-supply surges',
      polar: 'Polar watch',
    },
    korea: 'Republic of Korea',
    rotateWest: 'West',
    rotateEast: 'East',
    toKorea: 'Show Korea',
    toArctic: 'Show the Arctic',
    toAntarctic: 'Show Antarctica',
    unlocated: 'records not placed because their location could not be read',
    pick: 'Click a dot to see its records here',
    honesty:
      'Dots mark where reports or observations came from, not confirmed case locations · country-level dots sit at the country centre',
    card: {
      grade: { high: 'High', elevated: 'Elevated', watch: 'Watch' },
      intensity: 'Observation intensity',
      intensityNote:
        'Intensity = reports 20 · unexplained 15 · disaster 15 · trade 10 × log2(1+count) + CDC level × 8 (max 100) — an estimate, not a measurement; weights uncalibrated · not an outbreak probability',
      counts: 'Records received',
      travel: 'CDC travel notice',
      riskScore: 'Risk index (model estimate)',
      dominant: 'Main disease',
      korea: 'Link to Korea',
      koreaRoutes: 'Direct routes to Korea',
      koreaPassengers: 'Incheon passengers',
      koreaNone: 'No Korea link value for this country in the inflow report',
      koreaUnavailable: 'Korea inflow report could not be read, so no routes to Korea are drawn',
      arcNote: 'Red arcs = observed countries with air links to Korea → Seoul',
      evidence: 'Evidence',
      top: 'Highest intensity',
    },
  },
  sections: {
    events: {
      title: 'Outbreak reports by country',
      lead: 'Disease, place and event type extracted by AI from news and official sources · reported events, not confirmed case counts',
    },
    polar: {
      title: 'Polar and permafrost watch',
      lead: 'Thaw days and temperature trend are weather observations · thaw pressure and watch score are estimates computed from them · a watch, not an alert',
    },
    climate: {
      title: 'Climate (vector environment)',
      lead: 'Recent temperature and rainfall are observations · vector suitability and environmental pressure are model estimates, not measured outbreak risk',
    },
    trade: {
      title: 'Medical-supply import surges',
      lead: 'Import values are UN Comtrade customs statistics · reading them as outbreak preparedness is a proxy · reporting lag about 2 months',
    },
    disaster: {
      title: 'Post-disaster watch windows',
      lead: 'Disasters are measured by GDACS · watch windows (per-disease incubation spans) come from the literature and are not calibrated on this system · not a forecast',
    },
    travel: {
      title: 'Travel health notices (CDC)',
      lead: 'The official level 1–4 set by the US CDC, shown as is · may include non-infectious reasons',
    },
    land: {
      title: 'Forest fires (satellite)',
      lead: 'NASA FIRMS fire detections are measured · reading them as land clearing is a proxy',
    },
    forest: {
      title: 'Forest loss (satellite)',
      lead: 'Global Forest Watch forest-loss alert counts · subject to detection lag and confidence grades',
    },
    animal: {
      title: 'Animal disease (WOAH)',
      lead: 'Item count read from the official WOAH RSS · the old WAHIS API is retired, so outbreak counts are not determined',
    },
    genomic: {
      title: 'Genomic lineages (Nextstrain)',
      lead: 'Lineages that newly appeared in the last 60 days and the dominant lineages, from public genome builds',
    },
    social: {
      title: 'Social signal (Mastodon)',
      lead: '7-day post counts for disease hashtags on a single instance, mastodon.social · small sample, so its alert score is capped',
    },
    silence: {
      title: 'Reporting silence watch',
      lead: 'Whether a normally active reporting channel fell below half of its past average · a sign the reporting system may have broken down',
    },
    unexplained: {
      title: 'Unexplained signals',
      lead: 'Reports that match no known disease name · other conditions such as hospital-visit spikes are not measured for lack of data',
    },
  },
  polarTrend: {
    title: 'Polar trend (stored hourly)',
    lead: 'First stored value → latest value per region · temperature (mean daily max) and thaw days are weather observations; Δ (vs the same month’s 10-year mean) is computed · a record is added only when the value changes',
    span: 'About {days} day(s) stored — 30 days not reached yet (stored since 2026-11-15)',
    undetermined: '{n} record(s) unreadable at their time were left out of the trend (undetermined)',
    cols: { region: 'Region', first: 'First stored', latest: 'Latest', change: 'Change', records: 'Records' },
    empty: 'No polar values stored yet',
    unavailable: 'Could not read the polar history (undetermined)',
    wildlifeTitle: 'Antarctic Peninsula · H5N1 wildlife reports in the Antarctic and sub-Antarctic',
    wildlifeNote: 'H5 avian influenza records naming Antarctica, South Georgia or the Falklands among the latest 200 AI-extracted outbreak reports. Not confirmed; check the original.',
    wildlifeNone: 'No Antarctic or sub-Antarctic H5N1 reports in the latest extractions',
    wildlifeUnavailable: 'Could not read the extracted reports (undetermined)',
  },
  weekly: {
    metaTitle: 'Weekly import-risk report {week}: free beta',
    metaDescription: 'Weekly report on import risk to South Korea (free beta): country anomaly × air links to Korea, neighbouring-country weekly trends, CDC travel notices. Past reports kept.',
    eyebrow: 'Weekly report · free beta',
    title: 'Weekly report: import risk to South Korea',
    lead: 'The production server builds and keeps one report each week on its first collection cycle · country anomaly × air links to Korea · neighbouring-country weekly trends · CDC travel notices for the same countries',
    betaTitle: 'Free beta',
    betaBody: 'Free for anyone for now. Bookmark this page or download the Markdown below to paste into your own documents. There is no email subscription yet. If you would like to receive it, tell us through the contact page.',
    subscribe: 'Ask to receive it →',
    weeksLabel: 'Archived weeks',
    latest: 'latest',
    travelLabel: 'CDC travel notice',
    openCountry: 'Country page →',
    indexNote: 'The exposure index is for ranking. It is not a probability.',
    serverCaveats: 'Notes the server attached to this report (original Korean)',
    printHint: 'Use your browser’s print to save as PDF',
    missing: 'No report for {week}. Reports are built on each week’s first collection cycle, and earlier weeks may not have been kept.',
    unavailable: 'Could not read the report (undetermined): the server did not respond.',
  },
  korea: {
    eyebrow: 'KOREA VIEW · LIVE OBSERVATIONS',
    title: 'Observations linked to Korea right now',
    lead: 'Only the observations actually received by the production server that connect to Korea · re-read every 15 minutes',
    interpretation:
      'Built on the reading of the request as a national biosecurity view — to be changed if another meaning was intended',
    exposedTitle: 'Observed countries linked to Korea by air',
    exposedLead:
      'Countries with observations that have direct routes to Korea or Incheon passengers · ordered by observation intensity (an estimate)',
    trendsTitle: 'Neighbouring-country weekly trends',
    trendsLead:
      'Japan’s official weekly sentinel surveillance (IDWR) and the probability of an increase next week (a forecast, scored separately)',
    trendProb: 'Probability of increase next week (forecast)',
    domesticTitle: 'Unexplained signals in Korea',
    domesticLead: 'Reports not matching a known disease whose location reads as Korea',
    tradeTitle: 'Korea’s medical-supply imports',
    tradeLead:
      'From stored UN Comtrade surges (only the top 10 countries per product are stored) · reporting lag ~2 months',
    tradeNone:
      'Korea is not among the top surges in the last 90 days — not exhaustive, so this means "not in the top", not "no change"',
    securityTitle: 'Security view',
    gapsLabel: 'Pathogens currently signalled that have no international emergency stockpile (WHO ICG)',
    coveredLabel: 'Pathogens with an international emergency stockpile',
    gapsNote: 'National stockpiles are not public and are not examined · "exists" does not mean "sufficient"',
    highThreatLabel: 'Reports involving high-threat pathogens (in the latest 200 extractions)',
    highThreatNote: 'AI-structured report records, not confirmed case counts · count · places · latest date',
    empty: 'No such observation',
    unavailable: 'Could not be read (undetermined)',
    koreaUnavailable: 'The Korea inflow report could not be read, so the link to Korea is not determined',
  },
  country: {
    metaTitle: '{name} — Observation summary · AEGIRON',
    metaDescription:
      'What AEGIRON actually received about {name}: outbreak reports, unexplained signals, disasters, medical-supply imports, CDC travel notices, links to Korea, with a 30-day history.',
    eyebrow: 'COUNTRY OBSERVATIONS',
    back: '← Back to observations and globe',
    open: 'Open country page →',
    noCard:
      'No observations are grouped under this country right now — this means nothing was received, not that there is no risk',
    summaryTitle: 'Observation summary',
    evidenceTitle: 'Evidence',
    travelTitle: 'CDC travel notices',
    travelNone: 'No CDC travel notice names this country',
    koreaTitle: 'Link to Korea',
    historyTitle: '30-day observation history',
    historyLead:
      'Stored hourly · a new row appears only when the value changes · "undetermined" means it could not be read at that time (not zero) · history starts 2026-11-15',
    historyLayers: { climate: 'Climate', trade: 'Medical-supply imports', disaster: 'Disaster watch windows' },
    historyEmpty: 'No values stored in this period',
    historyUnavailable: 'Could not read the history (undetermined)',
    historyCols: {
      observed: 'First computed',
      confirmed: 'Last confirmed',
      measured: 'Measured (source)',
      derived: 'Derived (estimate)',
    },
    checklistTitle: 'Things to check',
    checklistLead:
      'A checklist generated by fixed rules from the kinds of observations received · not medical or public-health advice; check the original source first for every item',
    checks: {
      travel:
        'Read the CDC travel notice (area and level) and check whether guidance exists for travellers to and from that area',
      disaster:
        'A post-disaster watch window is open — check local reporting for new reports of the diseases in that window (within incubation)',
      trade:
        'Medical-supply imports are above usual — possibly preparation before an official announcement, but this is a proxy; check the products and the reporting lag (~2 months)',
      event:
        'Check the original source and date of each outbreak report — these are AI-structured records, not confirmed case counts',
      unexplained:
        'There are reports that do not match a known disease — read the original and check whether it is the same event reported again',
      korea:
        'Connected to Korea by air — the responsible agency judges whether quarantine or traveller guidance is needed, given direct routes and Incheon passenger volume',
      none: 'No observations received right now, so no checklist is generated',
    },
    responseTitle: 'Response measures in the affected country',
    responseNote:
      'Read with fixed keyword rules from the "Response" section of WHO Disease Outbreak News · measures WHO wrote in that report; extent, scope and effect are not judged · evidence is the WHO original · updated daily 21:00 UTC',
    responseEmpty:
      'No response record for this country in WHO Disease Outbreak News over the last 400 days — WHO did not publish one, or the section had none of the keywords',
    responseUnavailable: 'Could not read response records (undetermined)',
    responseCols: { date: 'Published', disease: 'Disease', measure: 'Measure', evidence: 'Evidence (WHO original)' },
    responseShared: 'Report covering several countries — not split by country',
    guidanceTitle: 'Standard response to stop spread — WHO references',
    guidanceLead:
      'Links, per disease observed in this country, to WHO outbreak guidance (case definitions, surveillance, testing, treatment, vaccines, communication) · not a prescription made by AEGIRON',
    guidanceToolbox: 'WHO outbreak toolbox',
    guidanceFactsheet: 'WHO fact sheet',
    guidanceIndex:
      'The guidance address for this disease could not be confirmed, so this links to the full list of WHO outbreak toolboxes',
    briefingOpen: 'Create notification briefing →',
    briefing: {
      metaTitle: '{name} — Observation briefing for notification (draft) · AEGIRON',
      eyebrow: 'NOTIFICATION BRIEFING · DRAFT',
      title: '{name} observation briefing',
      draftNotice: 'This is a draft to be reviewed and sent by a person · AEGIRON does not send it automatically',
      toLabel: 'To',
      toBlank:
        '(to be filled by the reviewer — e.g. the IHR focal point of the ministry of health or disease control agency)',
      fromLabel: 'From',
      generatedLabel: 'Generated',
      countryLabel: 'Country',
      s1: '1. What was observed (what · when · source)',
      s2: '2. Official sources (CDC travel notices · WHO response records)',
      s3: '3. Measured vs estimated',
      s4: '4. What could not be determined',
      s5: '5. Link to Korea',
      s6: '6. Nature of this document',
      nothing: 'None',
      estimateLine:
        'Observation intensity {n}/100 is an estimate combining the volume and weight of received observations, not a measurement · weights uncalibrated · not an outbreak probability',
      riskLine: 'Risk score {n} is a model estimate built from extracted reports and a vulnerability index',
      undeterminedHistory: 'History layers that could not be read: {layers}',
      undeterminedResponse: 'WHO response records could not be read',
      undeterminedKorea: 'The Korea inflow report could not be read, so the link to Korea is not determined',
      noUndetermined: 'Nothing was unreadable when this document was generated',
      disclaimer:
        'A summary of observations from public sources (reports, WHO, CDC, international statistics); not a diagnosis, a confirmed-case report or an official notification · check the original sources first · the same values are on AEGIRON’s observations page',
      printHint: 'Use the browser’s print (save as PDF) or copy the text',
      back: '← Back to country page',
    },
  },
};
