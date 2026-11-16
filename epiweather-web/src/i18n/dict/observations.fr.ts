import type { ContentPage, ObservationsDict } from '../types';

/** Tableau des observations (français). Valeurs mesurées et valeurs dérivées ne partagent jamais une colonne. */
export const observationsPageFr: ContentPage = {
  metaTitle: 'Observations — ce que AEGIRON mesure réellement',
  metaDescription:
    "Régions polaires et pergélisol, climat, commerce de fournitures médicales, catastrophes, avis aux voyageurs et signalements d'épidémies par pays : les valeurs mesurées que AEGIRON collecte en fonctionnement, par domaine.",
  eyebrow: 'OBSERVATIONS',
  title: 'Observations',
  lead: "Les valeurs que AEGIRON collecte réellement en fonctionnement, par domaine · lues depuis l'API de production · mises à jour toutes les quelques minutes",
  blocks: [],
};

export const observationsFr: ObservationsDict = {
  columns: {
    target: 'Objet',
    measured: 'Mesuré',
    derived: 'Dérivé (estimation · indicateur indirect)',
    time: 'À la date du',
    note: 'Remarque',
  },
  columnsNote:
    "Mesuré = valeur observée directement par la source · Dérivé = estimation calculée à partir de celle-ci, ou indicateur indirect d'autre chose — les deux ne sont jamais mélangés dans une même colonne",
  unavailable: "Impossible à lire sur le serveur de production pour l'instant — laissé vide plutôt qu'inventé",
  empty: 'Rien à afficher dans ce domaine pour le moment',
  sourceLabel: 'Source',
  countLabel: 'lignes',
  caveatKoLabel: 'Avertissement original (en coréen)',
  globe: {
    title: "Globe d'observation",
    lead: 'Les valeurs des tableaux ci-dessous placées sur un globe · taille du point = nombre de relevés pour ce pays ou cette région · faites glisser pour tourner',
    dragHint: 'Faites glisser pour tourner · cliquez sur un point pour le détail',
    layers: {
      event: "Signalements d'épidémies",
      unexplained: 'Signaux inexpliqués',
      disaster: 'Fenêtres après catastrophe',
      trade: 'Hausses de fournitures médicales',
      polar: 'Veille polaire',
    },
    korea: 'République de Corée',
    rotateWest: 'Ouest',
    rotateEast: 'Est',
    toKorea: 'Voir la Corée',
    toArctic: "Voir l'Arctique",
    toAntarctic: "Voir l'Antarctique",
    unlocated: "relevés non placés faute d'avoir pu lire le lieu",
    pick: 'Cliquez sur un point pour voir ses relevés ici',
    honesty:
      "Les points indiquent d'où viennent les signalements ou observations, pas l'emplacement de cas confirmés · les points nationaux sont placés au centre du pays",
    card: {
      grade: { high: 'Élevé', elevated: 'Vigilance', watch: 'Veille' },
      intensity: "Intensité d'observation",
      intensityNote:
        "Intensité = signalements 20 · inexpliqués 15 · catastrophes 15 · commerce 10 × log2(1+nombre) + niveau CDC × 8 (max 100) — estimation, pas une mesure ; pondération non calibrée · pas une probabilité d'épidémie",
      counts: 'Relevés reçus',
      travel: 'Avis CDC aux voyageurs',
      riskScore: 'Indice de risque (estimation du modèle)',
      dominant: 'Maladie principale',
      korea: 'Lien avec la Corée',
      koreaRoutes: 'Liaisons directes vers la Corée',
      koreaPassengers: 'Passagers à Incheon',
      koreaNone: 'Aucune valeur de lien avec la Corée pour ce pays dans le rapport',
      koreaUnavailable: "Rapport d'importation coréen illisible : aucune liaison vers la Corée n'est tracée",
      arcNote: 'Arcs rouges = pays observés reliés par avion à la Corée → Séoul',
      evidence: 'Éléments',
      top: 'Intensité la plus forte',
    },
  },
  sections: {
    events: {
      title: "Signalements d'épidémies par pays",
      lead: "Maladie, lieu et type d'événement extraits par IA de la presse et de sources officielles · événements signalés, pas des cas confirmés",
    },
    polar: {
      title: 'Veille polaire et pergélisol',
      lead: 'Jours de dégel et tendance de température sont des observations météo · pression de dégel et score de veille sont des estimations · une veille, pas une alerte',
    },
    climate: {
      title: 'Climat (environnement des vecteurs)',
      lead: "Température et précipitations récentes sont des observations · aptitude vectorielle et pression environnementale sont des estimations de modèle, pas un risque d'épidémie mesuré",
    },
    trade: {
      title: 'Hausses des importations de fournitures médicales',
      lead: "Valeurs d'importation issues des statistiques douanières UN Comtrade · les lire comme préparation à une épidémie est un indicateur indirect · délai de déclaration d'environ 2 mois",
    },
    disaster: {
      title: 'Fenêtres de veille après catastrophe',
      lead: "Catastrophes mesurées par GDACS · fenêtres (périodes d'incubation par maladie) tirées de la littérature, non calibrées sur ce système · pas une prévision",
    },
    travel: {
      title: 'Avis de santé aux voyageurs (CDC)',
      lead: 'Niveau officiel 1 à 4 fixé par les CDC américains, affiché tel quel · peut inclure des motifs non infectieux',
    },
    land: {
      title: 'Feux de forêt (satellite)',
      lead: 'Détections de feux NASA FIRMS mesurées · les lire comme du défrichement est un indicateur indirect',
    },
    forest: {
      title: 'Perte de forêt (satellite)',
      lead: 'Nombre d’alertes de perte forestière Global Forest Watch · délai de détection et niveaux de confiance',
    },
    animal: {
      title: 'Maladies animales (OMSA)',
      lead: "Nombre d'éléments lus dans le flux RSS officiel de l'OMSA · l'ancienne API WAHIS est retirée, le nombre de foyers n'est donc pas déterminé",
    },
    genomic: {
      title: 'Lignées génomiques (Nextstrain)',
      lead: 'Lignées apparues dans les 60 derniers jours et lignées dominantes, à partir des builds génomiques publics',
    },
    social: {
      title: 'Signal social (Mastodon)',
      lead: 'Publications sur 7 jours pour des hashtags de maladies sur une seule instance, mastodon.social · petit échantillon, score d’alerte plafonné',
    },
    silence: {
      title: 'Veille des silences de déclaration',
      lead: "Un canal de déclaration habituellement actif est-il tombé sous la moitié de sa moyenne passée · signe possible d'effondrement du système de déclaration",
    },
    unexplained: {
      title: 'Signaux inexpliqués',
      lead: "Signalements ne correspondant à aucun nom de maladie connu · d'autres conditions comme la hausse des consultations ne sont pas mesurées faute de données",
    },
  },
  country: {
    metaTitle: '{name} — Synthèse des observations · AEGIRON',
    metaDescription:
      'Ce qu’AEGIRON a réellement reçu sur {name} : signalements d’épidémies, signaux inexpliqués, catastrophes, importations de fournitures médicales, avis aux voyageurs du CDC, liens avec la Corée, avec un historique de 30 jours.',
    eyebrow: 'OBSERVATIONS PAR PAYS',
    back: '← Retour aux observations et au globe',
    open: 'Ouvrir la page du pays →',
    noCard:
      'Aucune observation n’est regroupée sous ce pays pour l’instant — cela signifie que rien n’a été reçu, pas qu’il n’y a aucun risque',
    summaryTitle: 'Synthèse des observations',
    evidenceTitle: 'Éléments',
    travelTitle: 'Avis aux voyageurs du CDC',
    travelNone: 'Aucun avis du CDC ne nomme ce pays',
    koreaTitle: 'Lien avec la Corée',
    historyTitle: 'Historique des observations sur 30 jours',
    historyLead:
      'Enregistré chaque heure · une nouvelle ligne n’apparaît que si la valeur change · « non déterminé » signifie illisible à ce moment-là (pas zéro) · historique depuis le 15/11/2026',
    historyLayers: {
      climate: 'Climat',
      trade: 'Importations de fournitures médicales',
      disaster: 'Fenêtres de surveillance post-catastrophe',
    },
    historyEmpty: 'Aucune valeur enregistrée sur cette période',
    historyUnavailable: 'Historique illisible (non déterminé)',
    historyCols: {
      observed: 'Premier calcul',
      confirmed: 'Dernière confirmation',
      measured: 'Mesure (source)',
      derived: 'Interprétation (estimation)',
    },
    checklistTitle: 'Points à vérifier',
    checklistLead:
      'Liste générée par des règles fixes selon les types d’observations reçues · ce n’est pas un avis médical ni sanitaire ; vérifiez d’abord la source d’origine pour chaque point',
    checks: {
      travel:
        'Lire l’avis du CDC (zone et niveau) et vérifier s’il existe des consignes pour les voyageurs en provenance ou à destination de cette zone',
      disaster:
        'Une fenêtre de surveillance post-catastrophe est ouverte — vérifier dans la presse locale les nouveaux signalements des maladies de cette fenêtre (dans la période d’incubation)',
      trade:
        'Les importations de fournitures médicales dépassent la normale — possible préparation avant une annonce officielle, mais c’est un indicateur indirect ; vérifier les produits et le délai de déclaration (~2 mois)',
      event:
        'Vérifier la source d’origine et la date de chaque signalement — ce sont des données structurées par IA, pas des cas confirmés',
      unexplained:
        'Certains signalements ne correspondent à aucune maladie connue — lire l’original et vérifier s’il s’agit du même événement rapporté à nouveau',
      korea:
        'Relié à la Corée par avion — l’autorité compétente juge si une quarantaine ou des consignes aux voyageurs sont nécessaires, au vu des liaisons directes et du trafic à Incheon',
      none: 'Aucune observation reçue pour l’instant, donc aucune liste n’est générée',
    },
    responseTitle: 'Mesures de riposte dans le pays touché',
    responseNote:
      'Pas encore extraites (non déterminé) — extraire des mesures comme confinement, quarantaine ou vaccination à partir des signalements demande une nouvelle extraction par IA ; c’est l’étape suivante',
  },
};
