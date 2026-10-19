import type { BaikalDict, ContentPage, SystemDict } from '../types';

/**
 * Système phare d’AEGIRON — Moteurs → YGGDRASIL → BAIKAL MOB (français). Voir baikal.ko.ts.
 * Typographie française du site : espace insécable ( ) avant : ; ? ! et à l’intérieur des « ».
 */

const NB = ' ';

export const systemsFr: SystemDict[] = [
  {
    code: 'HUGINN', name: 'Huginn', role: 'Veille',
    myth: 'Le corbeau d’Odin — survole le monde et rapporte ce qu’il voit',
    summary: 'Collecte chaque heure la presse locale de 178 pays en 52 langues et les données officielles nationales, et détecte les signaux anormaux.',
  },
  {
    code: 'MIMIR', name: 'Mimir', role: 'Extraction',
    myth: 'Le puits de sagesse — puise le sens dans le texte source',
    summary: 'Transforme le texte des articles et les tableaux PDF des rapports en signaux structurés — maladie, pays, cas, décès.',
  },
  {
    code: 'FORSETI', name: 'Forseti', role: 'Arbitrage',
    myth: 'Le dieu de la justice — décide de ce qui doit remonter',
    summary: 'Calcule l’indice de risque par pays et applique niveaux et plafonds journaliers pour ne transmettre que les alertes qui méritent l’attention.',
  },
  {
    code: 'SKULD', name: 'Skuld', role: 'Prévision et simulation',
    myth: 'La Norne de l’avenir — ce qui sera',
    summary: 'Enregistre le risque sous forme de prévisions et produit des scénarios de propagation, d’importation et d’intervention.',
  },
  {
    code: 'HEIMDALL', name: 'Heimdall', role: 'Génomique',
    myth: 'Le gardien du pont',
    summary: 'Suit les lignées dans les séquences publiques et réalise un criblage génomique défensif — le résultat est une priorité d’examen, pas un verdict.',
  },
  {
    code: 'VALHALLA', name: 'Valhalla', role: 'Contre-mesures',
    myth: 'La salle où se prépare la bataille',
    summary: 'Mesure, à partir de données publiques, les lacunes de couverture des stocks, de souveraineté de production et le pipeline clinique.',
  },
  {
    code: 'VAR', name: 'Var', role: 'Vérification',
    myth: 'La déesse des serments — veille sur les promesses et punit qui les rompt',
    summary: 'Vérifie les chiffres d’AEGIRON par le scellement des prévisions, leur notation face aux déclarations officielles et le registre d’avance.',
  },
];

export const baikalFr: BaikalDict = {
  flagshipEyebrow: 'SYSTÈME PHARE',
  flagshipTitle: 'Moteurs → YGGDRASIL → BAIKAL MOB',
  flagshipLead:
    'Désigné comme système phare d’AEGIRON. Sept systèmes moteurs sont reliés par l’ontologie YGGDRASIL, et BAIKAL MOB évalue, enregistre et publie chaque heure l’état de tout l’écosystème — une trace infalsifiable de la manière dont le système a réellement fonctionné.',
  layers: [
    {
      code: 'LAYER 1 · ENGINES',
      name: 'Sept systèmes moteurs',
      role: 'Veille → Vérification',
      body: '114 modules moteurs organisés en sept systèmes (HUGINN · MIMIR · FORSETI · SKULD · HEIMDALL · VALHALLA · VAR). Chaque moteur indique son mode de fonctionnement réel — horaire, quotidien, sur alerte ou à la demande.',
    },
    {
      code: 'LAYER 2 · ONTOLOGY',
      name: 'YGGDRASIL',
      role: 'Liaison',
      body: 'Définit les neuf flux de données qui circulent réellement entre les sept systèmes, chacun avec son emplacement dans le code et sa cadence, publiés au standard W3C JSON-LD.',
    },
    {
      code: 'LAYER 3 · STATE',
      name: 'BAIKAL MOB',
      role: 'Registre des changements d’état',
      body: 'Évalue et conserve chaque heure l’état des sept systèmes. Seuls les changements sont enregistrés, et rien n’est effacé. La boucle de rétroaction (vérité terrain → prévision → notation) est enregistrée en parallèle.',
    },
  ],
  statusTitle: 'État actuel de l’écosystème',
  statusLead:
    'Affiche tel quel le dernier instantané horaire enregistré par le serveur de production. Il n’existe que quatre états — normal, dégradé, arrêté et non évalué — et une valeur manquante n’est jamais comptée comme normale.',
  statusLabels: { ok: 'Normal', degraded: 'Dégradé', down: 'Arrêté', undetermined: 'Non évalué' },
  evidenceLabels: { measured: 'Mesuré', estimated: 'Estimé', proxy: 'Indicateur indirect' },
  scopeLabel: 'Périmètre',
  reasonLabel: 'Fondement',
  reasonOriginalNote: 'Les fondements sont affichés tels qu’enregistrés dans le journal de production (en coréen).',
  onRequestLabel: `Moteurs à la demande (pas d’état horaire)`,
  observedAt: 'Observé',
  staleNote: `Dernière observation il y a {n}${NB}minutes — le cycle horaire s’est peut-être arrêté, cet état n’est donc pas présenté comme actuel.`,
  notYet: 'Aucune observation horaire pour l’instant — elle apparaîtra après le prochain cycle de collecte.',
  unavailable: 'Impossible de lire l’état sur le serveur de production — ce message est affiché à la place d’une valeur inventée.',
  summaryLine: 'Normal {ok}/7 · dégradé {degraded} · arrêté {down} · non évalué {undetermined}',
  loopTitle: 'Boucle de rétroaction — vérité terrain → prévision → notation',
  loopSubject: 'Boucle de rétroaction',
  loopLead: 'Le chemin par lequel les prévisions d’AEGIRON sont notées face aux déclarations officielles ultérieures. Le flux de chacun des trois maillons est enregistré chaque heure.',
  loopStates: { measuring: 'En mesure', awaiting: 'En attente du premier résultat', empty: 'Vide', undetermined: 'Non évalué' },
  loopLinks: { ground_truth: '① Vérité terrain', predictions: '② Prévisions', scoring: '③ Notation' },
  loopFields: {
    live: 'Chargé en direct', other: 'Rétroactif, etc.', total: 'Total', named: 'Maladie nommée',
    resolved: 'Tranchées', unresolved: 'Ouvertes', earliestDue: 'Première échéance',
  },
  loopNote:
    `Tant qu’aucune prévision n’est tranchée, l’état est ${'«'}${NB}en attente du premier résultat${NB}${'»'} — non pas un taux de réussite de 0${NB}%, mais une mesure encore impossible. Les notes sont seulement consignées dans le registre${NB}; elles ne modifient pas automatiquement le modèle de prévision.`,
  transitionsTitle: 'Registre des changements d’état',
  transitionsLead: `Un registre d’audit tenu uniquement aux instants où un état a changé. La première observation est marquée ${'«'}${NB}début d’observation${NB}${'»'} — aucun état antérieur n’est inventé.`,
  transitionsEmpty: 'Aucun changement d’état enregistré',
  observationStart: 'Début d’observation',
  flowsTitle: 'YGGDRASIL — flux de données entre systèmes',
  flowsLead: 'Seuls les flux qui existent réellement dans le code sont représentés. Aucune liaison simplement plausible n’est ajoutée.',
  flows: [
    { id: 'huginn-mimir', from: 'HUGINN', to: 'MIMIR', kind: 'data', label: 'Texte source', cadence: `Quotidien 21${NB}h UTC` },
    { id: 'huginn-forseti', from: 'HUGINN', to: 'FORSETI', kind: 'data', label: 'Signaux d’anomalie', cadence: 'Horaire' },
    { id: 'mimir-forseti', from: 'MIMIR', to: 'FORSETI', kind: 'data', label: 'Signaux structurés', cadence: 'Horaire' },
    { id: 'heimdall-forseti', from: 'HEIMDALL', to: 'FORSETI', kind: 'data', label: 'Indicateurs de nouvelles lignées', cadence: 'Horaire' },
    { id: 'forseti-skuld', from: 'FORSETI', to: 'SKULD', kind: 'data', label: 'Risque → enregistrement de prévision', cadence: 'Horaire' },
    { id: 'skuld-var', from: 'SKULD', to: 'VAR', kind: 'data', label: 'Prévisions à sceller et noter', cadence: 'Horaire' },
    { id: 'mimir-var', from: 'MIMIR', to: 'VAR', kind: 'data', label: 'Candidats de vérité terrain (déclarations extraites)', cadence: `Quotidien 21${NB}h UTC` },
    { id: 'huginn-var', from: 'HUGINN', to: 'VAR', kind: 'data', label: 'Vérité terrain (annonces de l’OMS)', cadence: `Quotidien 21${NB}h UTC` },
    { id: 'var-skuld', from: 'VAR', to: 'SKULD', kind: 'feedback', label: 'Notes (consignation seule)', cadence: `Quotidien 21${NB}h UTC` },
  ],
  feedbackNote: 'Le flux de rétroaction VAR → SKULD est en consignation seule — les notes ne modifient pas automatiquement le modèle de prévision.',
  isolatedNote: 'VALHALLA est un axe indépendant qui n’alimente pas le calcul des alertes — il n’a aucun flux sortant et n’est pas représenté comme s’il en avait.',
  systemsTitle: 'Les sept systèmes moteurs',
  systemsLead: '114 modules moteurs organisés en sept systèmes. Les noms sont des noms de code internes — ni organismes réels, ni niveaux de classification, ni revendications de capacité.',
  colSystem: 'Système',
  colRole: 'Rôle',
  colEngines: 'Moteurs principaux',
  honestyTitle: 'Principes de fonctionnement',
  honestyPoints: [
    `Aucun état inventé — une valeur manquante est affichée ${'«'}${NB}non évalué${NB}${'»'}`,
    `Chaque système indique son périmètre — ce que ${'«'}${NB}normal${NB}${'»'} signifie réellement avoir observé`,
    `L’absence de données est distinguée de la panne — une donnée qui n’est simplement pas encore arrivée est marquée ${'«'}${NB}non évaluable${NB}${'»'}`,
    'Les moteurs qui ne tournent qu’à la demande (jumeau de propagation, Evo2, etc.) ne sont jamais présentés comme horaires',
    'Lecture seule par conception — BAIKAL MOB ne modifie aucun calcul d’alerte ou de prévision, et les alertes continuent de fonctionner même en cas de panne',
  ],
  openPage: 'Voir BAIKAL MOB en détail',
};

export const baikalPageFr: ContentPage = {
  metaTitle: 'BAIKAL MOB — le système phare d’AEGIRON',
  metaDescription:
    'Sept systèmes moteurs → ontologie YGGDRASIL → registre des changements d’état BAIKAL MOB. L’état de l’écosystème AEGIRON, évalué, conservé et publié chaque heure.',
  eyebrow: 'SYSTÈME PHARE',
  title: 'BAIKAL MOB — le système phare d’AEGIRON',
  lead:
    'La structure à trois couches Moteurs → YGGDRASIL → BAIKAL MOB est désignée comme système phare d’AEGIRON. Elle relie l’état de sept systèmes moteurs par une ontologie et enregistre et publie chaque heure les changements d’état de tout l’écosystème — comme le lac le plus profond et le plus ancien dépose son histoire couche après couche, le registre de fonctionnement s’accumule sans altération.',
  blocks: [],
  cta: {
    title: 'Vérifiez vous-même les mêmes données',
    body: 'Les API de production /api/baikal et /api/yggdrasil sont publiques — sans connexion, JSON-LD disponible.',
    label: 'Développeurs · API',
    href: 'developers',
  },
};
