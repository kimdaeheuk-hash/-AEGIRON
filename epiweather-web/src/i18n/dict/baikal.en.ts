import type { BaikalDict, ContentPage, SystemDict } from '../types';

/** AEGIRON flagship system — Engines → YGGDRASIL → BAIKAL MOB (English). See baikal.ko.ts. */

export const systemsEn: SystemDict[] = [
  {
    code: 'HUGINN', name: 'Huginn', role: 'Surveillance',
    myth: 'Odin’s raven — flies over the world and reports what it sees',
    summary: 'Collects local-language news from 178 countries in 52 languages and official national data every hour, and detects anomalous signals.',
  },
  {
    code: 'MIMIR', name: 'Mimir', role: 'Extraction',
    myth: 'The well of wisdom — draws meaning out of source text',
    summary: 'Turns article text and report PDF tables into structured signals: disease, country, cases, deaths.',
  },
  {
    code: 'FORSETI', name: 'Forseti', role: 'Judgment',
    myth: 'The god of judgment — decides what rises to the top',
    summary: 'Computes the country risk index and applies tiers and daily caps so that only alerts worth a person’s attention go out.',
  },
  {
    code: 'SKULD', name: 'Skuld', role: 'Forecasting & simulation',
    myth: 'The Norn of the future — what shall be',
    summary: 'Records risk as forecasts and produces spread, importation and intervention scenarios.',
  },
  {
    code: 'HEIMDALL', name: 'Heimdall', role: 'Genomics',
    myth: 'The watchman of the bridge',
    summary: 'Tracks lineages in public sequences and performs defensive genomic screening — the output is a review priority, not a verdict.',
  },
  {
    code: 'VALHALLA', name: 'Valhalla', role: 'Countermeasures',
    myth: 'The hall where the battle is prepared',
    summary: 'Measures stockpile coverage gaps, manufacturing-sovereignty gaps and the clinical pipeline from public data.',
  },
  {
    code: 'VAR', name: 'Var', role: 'Verification',
    myth: 'The goddess of oaths — watches promises and punishes those who break them',
    summary: 'Checks AEGIRON’s own numbers through sealed forecasts, scoring against official declarations and the lead-time ledger.',
  },
];

export const baikalEn: BaikalDict = {
  flagshipEyebrow: 'FLAGSHIP SYSTEM',
  flagshipTitle: 'Engines → YGGDRASIL → BAIKAL MOB',
  flagshipLead:
    'Designated as AEGIRON’s flagship system. Seven engine systems are connected by the YGGDRASIL ontology, and BAIKAL MOB assesses, records and publishes the state of the whole ecosystem every hour — a tamper-evident record of how the system itself actually ran.',
  layers: [
    {
      code: 'LAYER 1 · ENGINES',
      name: 'Seven engine systems',
      role: 'Surveillance → Verification',
      body: '116 engine modules organised into seven systems (HUGINN · MIMIR · FORSETI · SKULD · HEIMDALL · VALHALLA · VAR). Every engine states how it actually runs: hourly, daily, on alert or on request.',
    },
    {
      code: 'LAYER 2 · ONTOLOGY',
      name: 'YGGDRASIL',
      role: 'Connection',
      body: 'Defines the nine data flows that actually run between the seven systems, each with its code location and cadence, published in the W3C JSON-LD standard.',
    },
    {
      code: 'LAYER 3 · STATE',
      name: 'BAIKAL MOB',
      role: 'State-change record',
      body: 'Assesses and stores the state of all seven systems every hour. Only changes are recorded, and nothing is deleted. The feedback loop (ground truth → forecast → scoring) is recorded alongside.',
    },
  ],
  statusTitle: 'Current ecosystem state',
  statusLead:
    'Shows the latest hourly snapshot recorded by the production server, as is. There are only four states — OK, degraded, down and not assessed — and a missing value is never counted as OK.',
  statusLabels: { ok: 'OK', degraded: 'Degraded', down: 'Down', undetermined: 'Not assessed' },
  evidenceLabels: { measured: 'Measured', estimated: 'Estimated', proxy: 'Proxy' },
  scopeLabel: 'Scope',
  reasonLabel: 'Basis',
  reasonOriginalNote: 'The basis lines are shown as recorded in the production log (Korean).',
  onRequestLabel: 'On-request engines (no hourly state)',
  observedAt: 'Observed',
  staleNote: 'Last observation was {n} minutes ago — the hourly cycle may have stopped, so this is not shown as the current state.',
  notYet: 'No hourly observation yet — it will appear after the next collection cycle.',
  unavailable: 'Could not read the state from the production server — this message is shown instead of an invented value.',
  summaryLine: 'OK {ok}/7 · degraded {degraded} · down {down} · not assessed {undetermined}',
  loopTitle: 'Feedback loop — ground truth → forecast → scoring',
  loopSubject: 'Feedback loop',
  loopLead: 'The path by which AEGIRON’s forecasts are scored against later official declarations. The flow through each of the three links is recorded every hour.',
  loopStates: { measuring: 'Measuring', awaiting: 'Awaiting first result', empty: 'Empty', undetermined: 'Not assessed' },
  loopLinks: { ground_truth: '① Ground truth', predictions: '② Forecasts', scoring: '③ Scoring' },
  loopFields: {
    live: 'Live-ingested', other: 'Backfill etc.', total: 'Total', named: 'Disease named',
    resolved: 'Resolved', unresolved: 'Open', earliestDue: 'Earliest due date',
  },
  loopNote:
    'While no forecast has been resolved, the state is “awaiting first result” — not a 0% hit rate, but not yet measurable. Scores are recorded in the ledger only; they do not automatically modify the forecasting model.',
  weeklySubject: 'Weekly loop',
  weeklyTitle: 'Weekly trend forecast loop (separate from the 90-day loop)',
  weeklyFields: { scored: 'Scored', open: 'Pending', void: 'Not judged', brier: 'Brier', coin: 'coin', hits: 'Direction hits' },
  weeklyNotEnough: 'Results are published from {min} scored onward.',
  weeklyNote: 'Weekly forecasts resolve in one to two weeks, so this loop starts measuring well before the 90-day loop. Merging the two would make it look as if the 90-day outbreak forecasts were already being scored, so they are shown apart.',
  transitionsTitle: 'State-change record',
  transitionsLead: 'An audit record kept only at the moments a state changed. The first observation is marked “observation start” — no prior state is invented.',
  transitionsEmpty: 'No state changes recorded',
  observationStart: 'Observation start',
  flowsTitle: 'YGGDRASIL — data flows between systems',
  flowsLead: 'Only flows that actually exist in the code are drawn. Plausible-looking connections are not added.',
  flows: [
    { id: 'huginn-mimir', from: 'HUGINN', to: 'MIMIR', kind: 'data', label: 'Source text', cadence: 'Daily 21:00 UTC' },
    { id: 'huginn-forseti', from: 'HUGINN', to: 'FORSETI', kind: 'data', label: 'Anomaly signals', cadence: 'Hourly' },
    { id: 'mimir-forseti', from: 'MIMIR', to: 'FORSETI', kind: 'data', label: 'Structured signals', cadence: 'Hourly' },
    { id: 'heimdall-forseti', from: 'HEIMDALL', to: 'FORSETI', kind: 'data', label: 'New-lineage indicators', cadence: 'Hourly' },
    { id: 'forseti-skuld', from: 'FORSETI', to: 'SKULD', kind: 'data', label: 'Risk → forecast record', cadence: 'Hourly' },
    { id: 'skuld-var', from: 'SKULD', to: 'VAR', kind: 'data', label: 'Forecasts to seal and score', cadence: 'Hourly' },
    { id: 'mimir-var', from: 'MIMIR', to: 'VAR', kind: 'data', label: 'Ground-truth candidates (extracted declarations)', cadence: 'Daily 21:00 UTC' },
    { id: 'huginn-var', from: 'HUGINN', to: 'VAR', kind: 'data', label: 'Ground truth (WHO announcements)', cadence: 'Daily 21:00 UTC' },
    { id: 'var-skuld', from: 'VAR', to: 'SKULD', kind: 'feedback', label: 'Scores (record only)', cadence: 'Daily 21:00 UTC' },
  ],
  feedbackNote: 'The VAR → SKULD feedback flow is record-only — scores do not automatically modify the forecasting model.',
  isolatedNote: 'VALHALLA is an independent axis that does not feed the alert calculation — it has no outgoing flow, and is not drawn as if it did.',
  systemsTitle: 'The seven engine systems',
  systemsLead: '116 engine modules organised into seven systems. The names are internal code names — not real agencies, classification levels or capability claims.',
  colSystem: 'System',
  colRole: 'Role',
  colEngines: 'Key engines',
  honestyTitle: 'Operating principles',
  honestyPoints: [
    'No invented states — a missing value is shown as “not assessed”',
    'Every system states its scope — what “OK” was actually observed to mean',
    'Missing data is distinguished from failure — data that has simply not arrived yet is marked “not assessable”',
    'Engines that run only on request (spread twin, Evo2, etc.) are never shown as running hourly',
    'Read-only by design — BAIKAL MOB does not change alert or forecast calculations, and alerts keep working even if it fails',
  ],
  openPage: 'See BAIKAL MOB in detail',
};

export const baikalPageEn: ContentPage = {
  metaTitle: 'BAIKAL MOB — AEGIRON’s flagship system',
  metaDescription:
    'Seven engine systems → YGGDRASIL ontology → BAIKAL MOB state-change record. The state of the AEGIRON ecosystem, assessed, stored and published every hour.',
  eyebrow: 'FLAGSHIP SYSTEM',
  title: 'BAIKAL MOB — AEGIRON’s flagship system',
  lead:
    'The three-layer structure Engines → YGGDRASIL → BAIKAL MOB is designated as AEGIRON’s flagship system. It connects the state of seven engine systems through an ontology and records and publishes the state changes of the whole ecosystem every hour — like the deepest, oldest lake laying down its history layer by layer, the operating record accumulates without alteration.',
  blocks: [],
  cta: {
    title: 'Check the same data yourself',
    body: 'The production APIs /api/baikal and /api/yggdrasil are public — no login, JSON-LD available.',
    label: 'Developers · API',
    href: 'developers',
  },
};
