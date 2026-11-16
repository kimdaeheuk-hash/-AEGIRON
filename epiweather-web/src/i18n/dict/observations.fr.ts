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
  polarTrend: {
    title: 'Évolution polaire (enregistrée chaque heure)',
    lead: 'Première valeur enregistrée → valeur la plus récente par région · température (moyenne des maxima) et jours de dégel = observations météo ; Δ (par rapport à la moyenne décennale du même mois) = calcul · un enregistrement n’est ajouté que si la valeur change',
    span: 'Environ {days} jour(s) enregistré(s) — 30 jours pas encore atteints (enregistré depuis le 15/11/2026)',
    undetermined: '{n} enregistrement(s) illisible(s) à leur heure exclu(s) de l’évolution (non déterminé)',
    cols: {
      region: 'Région',
      first: 'Première valeur',
      latest: 'Plus récente',
      change: 'Variation',
      records: 'Enregistrements',
    },
    empty: 'Aucune valeur polaire enregistrée pour l’instant',
    unavailable: 'Historique polaire illisible (non déterminé)',
    wildlifeTitle: 'Péninsule Antarctique · signalements de H5N1 chez la faune antarctique et subantarctique',
    wildlifeNote: 'Enregistrements de grippe aviaire H5 citant l’Antarctique, la Géorgie du Sud ou les Malouines parmi les 200 derniers rapports extraits par IA. Non confirmé ; vérifier la source.',
    wildlifeNone: 'Aucun signalement H5N1 antarctique ou subantarctique dans les dernières extractions',
    wildlifeUnavailable: 'Rapports extraits illisibles (non déterminé)',
  },
  weekly: {
    metaTitle: 'Rapport hebdomadaire de risque d’importation {week} — bêta gratuite',
    metaDescription: 'Rapport hebdomadaire sur le risque d’importation vers la Corée du Sud (bêta gratuite) : anomalie par pays × liaisons aériennes, tendances hebdomadaires d’un pays voisin, avis de voyage du CDC. Rapports passés conservés.',
    eyebrow: 'Rapport hebdomadaire · bêta gratuite',
    title: 'Rapport hebdomadaire : risque d’importation vers la Corée du Sud',
    lead: 'Le serveur de production établit et conserve un rapport par semaine, au premier cycle de collecte · anomalie par pays × liaisons aériennes avec la Corée · tendances hebdomadaires d’un pays voisin · avis de voyage du CDC pour les mêmes pays',
    betaTitle: 'Bêta gratuite',
    betaBody: 'Gratuit pour tous pour l’instant. Ajoutez cette page à vos favoris ou téléchargez le Markdown ci-dessous pour l’intégrer à vos documents. Il n’y a pas encore d’abonnement par e-mail : pour le recevoir, écrivez-nous via la page contact.',
    subscribe: 'Demander à le recevoir →',
    weeksLabel: 'Semaines archivées',
    latest: 'dernier',
    travelLabel: 'Avis de voyage CDC',
    openCountry: 'Page pays →',
    indexNote: 'L’indice d’exposition sert au classement. Ce n’est pas une probabilité.',
    serverCaveats: 'Remarques jointes par le serveur à ce rapport (coréen d’origine)',
    printHint: 'Utilisez l’impression du navigateur pour enregistrer en PDF',
    missing: 'Aucun rapport pour {week}. Les rapports sont établis au premier cycle de collecte de chaque semaine ; les semaines antérieures peuvent ne pas avoir été conservées.',
    unavailable: 'Impossible de lire le rapport (non déterminé) : le serveur n’a pas répondu.',
  },
  korea: {
    eyebrow: 'VUE CORÉE · OBSERVATIONS EN DIRECT',
    title: 'Observations liées à la Corée en ce moment',
    lead: 'Uniquement les observations réellement reçues par le serveur de production qui concernent la Corée · relues toutes les 15 minutes',
    interpretation:
      'Construit en lisant la demande comme une vue de biosécurité nationale — à changer si un autre sens était voulu',
    exposedTitle: 'Pays observés reliés à la Corée par avion',
    exposedLead:
      'Pays avec observations ayant des liaisons directes vers la Corée ou des passagers à Incheon · par intensité d’observation (estimation)',
    trendsTitle: 'Tendances hebdomadaires des pays voisins',
    trendsLead:
      'Surveillance sentinelle hebdomadaire officielle du Japon (IDWR) et probabilité de hausse la semaine suivante (prévision, évaluée à part)',
    trendProb: 'Probabilité de hausse la semaine suivante (prévision)',
    domesticTitle: 'Signaux inexpliqués en Corée',
    domesticLead: 'Signalements ne correspondant à aucune maladie connue et localisés en Corée',
    tradeTitle: 'Importations de fournitures médicales de la Corée',
    tradeLead:
      'D’après les hausses UN Comtrade enregistrées (seuls les 10 premiers pays par produit) · délai de déclaration ~2 mois',
    tradeNone:
      'La Corée ne figure pas parmi les plus fortes hausses des 90 derniers jours — liste non exhaustive : « absent du haut du classement », pas « aucun changement »',
    securityTitle: 'Vue sécurité',
    gapsLabel: 'Pathogènes actuellement signalés sans stock d’urgence international (ICG de l’OMS)',
    coveredLabel: 'Pathogènes disposant d’un stock d’urgence international',
    gapsNote:
      'Les stocks nationaux ne sont pas publics et ne sont pas examinés · « existe » ne veut pas dire « suffisant »',
    highThreatLabel: 'Signalements impliquant des pathogènes à haut risque (parmi les 200 dernières extractions)',
    highThreatNote: 'Données structurées par IA, pas des cas confirmés · nombre · lieux · dernière date',
    empty: 'Aucune observation de ce type',
    unavailable: 'Illisible (non déterminé)',
    koreaUnavailable:
      'Le rapport sur les entrées en Corée n’a pas pu être lu ; le lien avec la Corée n’est pas déterminé',
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
      'Lu par des règles de mots-clés fixes dans la section « Riposte » des Bulletins d’information sur les flambées de l’OMS · mesures que l’OMS a écrites dans ce bulletin ; ampleur, portée et effet non évalués · élément = texte original de l’OMS (anglais) · mis à jour chaque jour à 21 h UTC',
    responseEmpty:
      'Aucune riposte enregistrée pour ce pays dans les bulletins de l’OMS des 400 derniers jours — l’OMS n’en a pas publié, ou la section ne contenait aucun mot-clé',
    responseUnavailable: 'Impossible de lire les ripostes (non déterminé)',
    responseCols: { date: 'Publié', disease: 'Maladie', measure: 'Mesure', evidence: 'Élément (texte OMS)' },
    responseShared: 'Bulletin couvrant plusieurs pays — non ventilé par pays',
    guidanceTitle: 'Riposte standard pour freiner la propagation — références OMS',
    guidanceLead:
      'Liens, pour chaque maladie observée dans ce pays, vers les orientations de l’OMS (définitions de cas, surveillance, tests, traitement, vaccins, communication) · ce n’est pas une prescription d’AEGIRON',
    guidanceToolbox: 'Boîte à outils OMS de riposte aux flambées',
    guidanceFactsheet: 'Aide-mémoire OMS',
    guidanceIndex:
      'L’adresse des orientations pour cette maladie n’a pas pu être confirmée ; le lien mène à la liste complète des boîtes à outils de l’OMS',
    briefingOpen: 'Créer le briefing de notification →',
    briefing: {
      metaTitle: '{name} — Briefing d’observation pour notification (projet) · AEGIRON',
      eyebrow: 'BRIEFING DE NOTIFICATION · PROJET',
      title: 'Briefing d’observation — {name}',
      draftNotice: 'Projet à relire puis envoyer par une personne · AEGIRON ne l’envoie pas automatiquement',
      toLabel: 'Destinataire',
      toBlank:
        '(à compléter par le relecteur — p. ex. le point focal RSI du ministère de la santé ou de l’agence de contrôle des maladies)',
      fromLabel: 'Expéditeur',
      generatedLabel: 'Généré le',
      countryLabel: 'Pays',
      s1: '1. Ce qui a été observé (quoi · quand · source)',
      s2: '2. Sources officielles (avis du CDC · ripostes enregistrées par l’OMS)',
      s3: '3. Mesure ou estimation',
      s4: '4. Ce qui n’a pas pu être déterminé',
      s5: '5. Lien avec la Corée',
      s6: '6. Nature de ce document',
      nothing: 'Aucun',
      estimateLine:
        'L’intensité d’observation {n}/100 est une estimation combinant le volume et le poids des observations reçues, pas une mesure · pondération non calibrée · pas une probabilité d’épidémie',
      riskLine:
        'Le score de risque {n} est une estimation de modèle fondée sur les signalements extraits et un indice de vulnérabilité',
      undeterminedHistory: 'Couches d’historique illisibles : {layers}',
      undeterminedResponse: 'Les ripostes enregistrées par l’OMS n’ont pas pu être lues',
      undeterminedKorea:
        'Le rapport sur les entrées en Corée n’a pas pu être lu ; le lien avec la Corée n’est pas déterminé',
      noUndetermined: 'Aucune source illisible lors de la génération de ce document',
      disclaimer:
        'Synthèse d’observations issues de sources publiques (presse, OMS, CDC, statistiques internationales) ; ce n’est ni un diagnostic, ni une déclaration de cas confirmés, ni une notification officielle · vérifiez d’abord les sources d’origine · les mêmes valeurs figurent sur la page Observations d’AEGIRON',
      printHint: 'Utilisez l’impression du navigateur (enregistrer en PDF) ou copiez le texte',
      back: '← Retour à la page du pays',
    },
  },
};
