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

  transparency: {
    metaTitle: 'What we don’t know — unvalidated areas and known limits',
    metaDescription:
      'Everything AEGIRON has not yet validated, its known limits, and its data gaps — plus how the system checks its own numbers.',
    eyebrow: 'WHAT WE DON’T KNOW',
    title: 'What we don’t know',
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
    metaTitle: 'About',
    metaDescription:
      'AEGIRON builds infectious disease early-warning systems from Busan, South Korea. Here is exactly what stage we are at.',
    eyebrow: 'ABOUT',
    title: 'AEGIRON',
    lead: 'We build a system that catches infectious disease signals before they become international news. We are based in Busan, South Korea.',
    blocks: [
      {
        title: 'Where we are',
        body: 'Early stage. We will not blur that — due diligence surfaces it anyway, and blurring it costs credibility on everything else we say.',
        points: [
          'The system genuinely runs. Signals arrive hourly from 21 sources and the dashboard is open right now.',
          'We have no commercial customers yet. We are looking for a first partner.',
          'No external body has independently reviewed the system.',
          'There is no validated forecast track record. Continued operation accumulates one on its own.',
        ],
      },
      {
        title: 'Why publish everything',
        body: 'Creating things to hide at a stage with no customers and no contracts turns into debt the moment anyone verifies you. Opening everything now leaves us verifiable instead. It is also a choice larger competitors cannot easily copy — they have contracts to protect.',
      },
      {
        title: 'Where this goes',
        items: [
          { title: 'Near term', body: 'Connect with field organisations and surveillance networks to get closer to the source of signals.' },
          { title: 'Medium term', body: 'Keep operating so a verifiable forecast record accumulates, with sealed records as its evidence.' },
          { title: 'Long term', body: 'Become a system actually used in the regions with the largest surveillance gaps.' },
        ],
      },
    ],
    cta: {
      title: 'If this seems worth a conversation',
      body: 'Reinsurance, government, multilateral or field organisation — all welcome.',
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
