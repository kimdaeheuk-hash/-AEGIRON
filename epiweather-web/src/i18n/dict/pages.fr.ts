import type { PagesDict } from '../types';

/**
 * Contenu français des pages secondaires.
 *
 * ★ Les chiffres ici sont des valeurs mesurées ★
 * 23 sources de collecte opérationnelles · 118 modules algorithmiques (116 moteurs + YGGDRASIL · BAIKAL) · 128 points d’accès · 2 263 tests automatisés (mesuré le 2026-10-19).
 * Aucune estimation n’est présentée comme un fait.
 *
 * ★ RÈGLE ABSOLUE ★ Aucune affirmation de précision ni de délai d’avance.
 */
export const pagesFr: PagesDict = {
  platform: {
    metaTitle: 'Plateforme — le monde entier comme une seule veille',
    metaDescription:
      'AEGIRON collecte la presse locale de 178 pays en 52 langues, ainsi que les données de surveillance officielles, et les traite en cinq étapes — collecter, extraire, juger, prévoir, répondre.',
    eyebrow: 'PLATFORM',
    title: 'Le monde entier comme une seule veille',
    lead: 'La maladie n’attend pas aux frontières. AEGIRON relie la presse locale de 178 pays, les données officielles de chaque nation et les signaux environnementaux, commerciaux et génomiques en un seul système, et calcule chaque heure où quelque chose s’écarte de la normale. Voici les cinq étapes qu’un signal traverse pour devenir une alerte et un scénario de réponse.',
    blocks: [
      {
        title: 'La plateforme en un coup d’œil',
        kicker: 'AT A GLANCE',
        tone: 'teal',
        specs: [
          { label: 'Portée de veille', value: '178 pays · 52 langues de presse locale (179 flux)' },
          { label: 'Sources en direct', value: '23 · collectées automatiquement chaque heure' },
          { label: 'Modèle de propagation', value: '159 pays · 1 671 liaisons aériennes · 314 frontières terrestres' },
          { label: 'Modules algorithmiques', value: '118 (116 moteurs · ontologie YGGDRASIL · couche d’état BAIKAL MOB)' },
          { label: 'API publique', value: '128 points d’accès' },
          { label: 'Contrôle qualité', value: '2 263 tests automatisés — tous doivent passer avant toute mise en production' },
        ],
        note: 'Mesuré sur le dépôt et les journaux d’exploitation le 2026-10-19.',
      },
      {
        title: '01 · Collecter',
        kicker: 'STAGE 01',
        tone: 'teal',
        body: 'Les signaux arrivent chaque heure de 23 sources opérationnelles. Des matériaux aussi différents que des rapports officiels d’organismes internationaux et la presse en langue locale de 178 pays sont normalisés en un seul format de signal, et chaque source porte son propre poids de fiabilité dans tous les calculs ultérieurs.',
        items: [
          { title: 'Déclarations officielles', body: 'Bureaux régionaux de l’OMS pour l’Afrique et les Amériques, Agence coréenne de contrôle des maladies, bulletin hebdomadaire japonais, Centre de protection de la santé de Hong Kong et InfoDengue (Brésil). Nous respectons le niveau de gravité fixé par chaque organisme.' },
          { title: 'Presse en langue locale', body: 'La première couverture locale avant la traduction par la presse internationale — tenue au même standard, même dans les régions aux grandes lacunes de veille.' },
          { title: 'Signaux environnementaux et précurseurs', body: 'La surveillance des eaux usées (CDC NWSS), une fenêtre de veille post-catastrophe (GDACS), l’observation polaire et les statistiques commerciales de fournitures médicales saisissent d’abord les changements de conditions et de comportements de préparation.' },
        ],
      },
      {
        title: '02 · Extraire',
        kicker: 'STAGE 02',
        tone: 'sky',
        body: 'Maladie, pays, cas et décès sont structurés à partir des tableaux PDF et du texte des articles. La règle est claire — seules les valeurs confirmées deviennent des chiffres.',
        points: [
          'Seules les colonnes dont le sens est confirmé par l’en-tête sont utilisées. Rien n’est deviné par position, donc les chiffres ne dérivent pas en silence.',
          '« Nouveaux cas sur sept jours » et « cumul », « suspect » et « confirmé » sont tenus pour des champs distincts.',
          'Une ligne « total » n’est pas un pays et est exclue, pour garder l’analyse des tendances propre.',
          'Les chiffres extraits sont confrontés au texte source, et l’emplacement de la source est consigné.',
        ],
      },
      {
        title: '03 · Juger',
        kicker: 'STAGE 03',
        tone: 'crimson',
        body: 'Les anomalies sont calculées **par rapport au niveau habituel de ce pays et de cet indicateur,** non en valeur absolue. Les mêmes cinq cas n’ont pas le même sens dans un pays qui déclare sans cesse et dans un pays habituellement silencieux.',
        points: [
          'Les scores d’anomalie viennent de l’écart à une ligne de base par pays et par indicateur et du standard CDC EARS.',
          'Les signaux anciens contribuent de moins en moins avec le temps (décroissance à demi-vie).',
          '« Mesuré et jugé normal » est distingué de « aucune donnée pour juger ».',
          'Les alertes portent un plafond quotidien par niveau, pour que seul l’essentiel remonte.',
        ],
      },
      {
        title: '04 · Prévoir',
        kicker: 'STAGE 04',
        tone: 'indigo',
        body: 'Des modèles de transmission estiment l’ampleur de la propagation et les voies d’importation entre pays, en simulant avec des paramètres propres à la maladie sur un réseau aérien et terrestre reliant 159 pays.',
        points: [
          'Les modèles sont ajustés avec le R0 et la létalité propres à chaque maladie, mesurés dans la littérature.',
          'Les pathogènes à transmission par contact reçoivent leur propre **population atteignable**, pour une échelle réaliste.',
          'Les estimations de décès modélisées sont confrontées automatiquement aux plus grandes épidémies connues, et un avertissement accompagne toute valeur hors de cet intervalle.',
        ],
      },
      {
        title: '05 · Répondre',
        kicker: 'STAGE 05',
        tone: 'forest',
        body: 'Nous ne nous arrêtons pas à « ce qui arrive ». Les scénarios sans réponse et avec intervention sont comparés pour montrer quelles mesures, à quelle intensité, cassent la transmission.',
        items: [
          { title: 'Référence sans réponse', body: 'La trajectoire sans aucune mesure sert de référence.' },
          { title: 'Comparer les interventions', body: 'Des combinaisons d’isolement, de distanciation, de vaccination et de traitement sont testées pour trouver où le nombre de reproduction effectif passe sous 1.' },
          { title: 'Scellement des prévisions', body: 'Prévisions et scénarios sont scellés par une empreinte au moment de leur production, pour qu’un tiers puisse vérifier ce que nous avons prévu, et quand.' },
        ],
      },
    ],
    cta: {
      title: 'Voyez les cinq étapes tourner par vous-même',
      body: 'Sur le tableau de bord en direct, regardez toute la chaîne — de la collecte à la réponse — tourner en temps réel, sans connexion.',
      label: 'Ouvrir le tableau de bord',
      href: '/dashboard',
    },
  },

  techSpec1: {
    metaTitle: 'Technologie I — veille et collecte',
    metaDescription:
      'Veille de la presse en langue locale sur 178 pays et 52 langues, extraction automatique des rapports officiels en PDF, indicateurs précurseurs environnementaux, commerciaux et d’appels d’offres, indice d’anomalie à six couches, veille des silences, détection à deux étages et veille de la santé des sources — la fiche technique et les moteurs de la couche de veille d’AEGIRON.',
    eyebrow: 'TECHNOLOGY · I',
    title: 'Veille et collecte',
    lead: 'La première couche d’AEGIRON est une veille qui balaie la planète entière chaque heure. Elle tourne d’elle-même, cherchant ce qui « s’écarte de la normale » dans la presse locale, les bulletins officiels, les signaux environnementaux, les registres commerciaux et d’appels d’offres. La fiche technique d’abord, puis chaque moteur.',
    photo: {
      src: '/media/photos/iss-city-lights.jpg',
      alt: 'Lumières urbaines de nuit vues depuis la Station spatiale internationale',
      caption: 'La Türkiye de nuit, vue depuis la Station spatiale internationale. Les réseaux qui font circuler personnes et marchandises sont aussi les voies d’une épidémie.',
      credit: 'NASA JSC · Domaine public',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:The_city_lights_of_T%C3%BCrkiye_sparkle_below_the_International_Space_Station_(iss074e0225549).jpg',
    },
    blocks: [
      {
        title: 'Couche de veille — fiche technique',
        kicker: 'SPEC SHEET',
        tone: 'teal',
        specs: [
          { label: 'Presse en langue locale', value: '178 pays · 52 langues · 179 flux · horaire' },
          { label: 'Classification des articles', value: 'Classifieur de titres par LLM (uniquement les vrais foyers) + repli par mots-clés' },
          { label: 'Déclarations officielles', value: 'Bureaux régionaux de l’OMS · 6 autorités sanitaires nationales · WHO IRIS' },
          { label: 'Extraction documentaire', value: 'Structuration des tableaux PDF (modèle documentaire NVIDIA) → signal normalisé → tendance' },
          { label: 'Indice d’anomalie', value: 'Somme pondérée à six couches (officielle · officieuse · comportementale · environnementale · animale · inexpliquée)' },
          { label: 'Détection standard', value: 'CDC EARS C1 · C2 · C3 + ligne de base par z-score et par pays' },
          { label: 'Architecture de détection', value: 'Sentinelle (rapide) → couche de vérification (recoupement), deux étages' },
          { label: 'Fiabilité d’exploitation', value: 'Santé des sources · invariants de qualité · registre de capacités — autocontrôle à chaque cycle' },
        ],
      },
      {
        title: 'Veille de la presse en langue locale',
        kicker: 'ENGINE · local_news',
        tone: 'teal',
        body: 'Avant que la presse internationale ne le traduise, le premier signal est souvent un article en langue locale. Nous prenons 178 pays dans l’actualité agrégée par pays et par langue, mesurons la densité du vocabulaire épidémiologique, et un modèle de langage lit les titres pour ne retenir que les articles d’un vrai foyer ou cluster. Nous n’écartons pas les pays à faible risque — une pandémie peut commencer n’importe où.',
        points: [
          'L’unité de détection est le croisement pays × langue × maladie — un pays dans une seule fenêtre d’agrégation.',
          'Les régions que les services commerciaux couvrent rarement — Afrique, Asie centrale, États insulaires du Pacifique — sont surveillées au même standard.',
          'Quand plusieurs flux rapportent le même événement, un regroupement translingue les réunit en un seul.',
          'Si la source principale est bloquée, un fournisseur de titres de repli prend le relais automatiquement, pour que la veille ne s’arrête jamais.',
        ],
      },
      {
        title: 'Extraction automatique des rapports officiels',
        kicker: 'ENGINE · who_iris → pdf_table_extract → bulletin_*',
        tone: 'sky',
        body: 'Dans bien des documents — le rapport hebdomadaire de situation de l’OMS Afrique, par exemple — les chiffres clés par pays et par maladie ne vivent que dans des tableaux PDF. AEGIRON récupère les rapports depuis le dépôt documentaire de l’OMS, restitue les tableaux avec un modèle documentaire, les convertit en signaux normalisés, les charge, et relie les éditions successives en une tendance.',
        items: [
          { title: 'Récupération', body: 'Télécharge de façon fiable les rapports hebdomadaires depuis WHO IRIS. Les éditions déjà chargées ne sont pas récupérées à nouveau.', meta: 'who_iris · bulletin_collect' },
          { title: 'Restitution des tableaux', body: 'Restitue les tableaux PDF en structure lignes-colonnes avec le modèle documentaire NVIDIA.', meta: 'pdf_table_extract' },
          { title: 'Signalisation · chargement', body: 'Sépare « 7 jours », « cumul », « suspect » et « confirmé » et les charge dans la forme que lit le moteur d’alerte.', meta: 'bulletin_signals · bulletin_ingest' },
          { title: 'Tendance', body: 'Transforme les signaux ponctuels par édition en série temporelle pour voir vitesse et direction.', meta: 'bulletin_trend' },
        ],
      },
      {
        title: 'Indicateurs précurseurs — environnement · commerce · appels d’offres',
        kicker: 'ENGINE · disaster_watch · polar_* · comtrade_signals · procurement_watch',
        tone: 'forest',
        body: 'Les épidémies laissent d’abord des traces hors du système de santé. Catastrophes, climat, changements polaires, importations de fournitures médicales et avis d’appels d’offres ne sont pas l’épidémie elle-même, mais des signaux de ses conditions et des comportements de préparation. AEGIRON les surveille comme une couche distincte.',
        items: [
          { title: 'Fenêtre post-catastrophe', body: 'Après inondations, séismes et tempêtes, le pays est surveillé à un seuil plus bas pendant la fenêtre où le risque hydrique et vectoriel monte.', meta: 'disaster_watch · GDACS' },
          { title: 'Polaire · glaciers', body: 'Changements du pergélisol et de 27 régions montagneuses glaciaires, observés avec ligne de base et tendance.', meta: 'polar_signals · polar_baseline · polar_trend · glacier_regions' },
          { title: 'Climat · forêts', body: 'Anomalies de température et de pluie et pertes/feux de forêt lus comme indicateurs de conditions de débordement.', meta: 'climate_signals · forest_signals · deforestation_signals' },
          { title: 'Commerce de fournitures médicales', body: 'UN Comtrade détecte les flambées d’importation de masques, d’EPI et de tests par pays.', meta: 'comtrade_signals' },
          { title: 'Appels d’offres publics', body: 'Suit les mouvements d’achat liés à la biosécurité dans le système d’appels d’offres public coréen.', meta: 'procurement_watch' },
          { title: 'Eaux usées · animal', body: 'Concentration de pathogènes dans les stations d’épuration américaines et rapports d’épizooties de l’OMSA.', meta: 'CDC NWSS · wahis' },
        ],
      },
      {
        title: 'Indice d’anomalie à six couches et détection standard',
        kicker: 'ENGINE · gai · ears · anomaly_engine · kdca_anomaly',
        tone: 'crimson',
        body: 'Les signaux de six couches — officielle, officieuse, comportementale, environnementale, animale et inexpliquée — sont convertis en scores d’anomalie par rapport à leur niveau habituel, pondérés par la fiabilité de la source, puis combinés en un seul indice (GAI). Au-dessus se tient le standard de la surveillance épidémiologique, les CDC américains EARS C1/C2/C3, stable même là où la ligne de base est courte.',
        points: [
          'Chaque signal est scoré en z-score par rapport à sa propre distribution historique, la dernière valeur étant exclue de la ligne de base.',
          'Chaque couche porte une pondération de fiabilité différente — données officielles et publications sociales ne peuvent peser pareil.',
          'EARS utilise une bande de garde pour que les valeurs de début d’épidémie ne contaminent pas la ligne de base.',
          'Les maladies à déclaration obligatoire en Corée sont surveillées maladie par maladie, pour qu’un mouvement individuel ne se perde pas dans le total.',
        ],
      },
      {
        title: 'Silences de déclaration · inexpliqués · pathogènes à haut risque',
        kicker: 'ENGINE · negative_space · unexplained · pathogen_sentinel',
        tone: 'violet',
        body: 'Le danger ne vient pas seulement quand les chiffres montent. AEGIRON surveille trois types que le simple décompte manque, chacun avec un moteur dédié.',
        items: [
          { title: 'Veille des silences', body: 'Quand un canal actif tombe sous la moitié de sa ligne de base, c’est un signal. Elle vise les cas, comme Ebola en Guinée en 2014, où le système de déclaration s’effondre avant la propagation.', meta: 'negative_space' },
          { title: 'Foyers inexpliqués', body: 'Compte les foyers qui ne correspondent à aucun profil de maladie connu. La pneumonie d’origine inconnue de Wuhan en décembre 2019 est du type.', meta: 'unexplained' },
          { title: 'Rapports uniques à haut risque', body: 'Pour des pathogènes comme la peste, l’anthrax et la variole — où un seul événement est déjà une nouvelle — il remonte un rapport unique sans attendre l’accumulation.', meta: 'pathogen_sentinel' },
        ],
      },
      {
        title: 'Détection à deux étages et fiabilité d’exploitation',
        kicker: 'ENGINE · sentinel · verification · source_health · quality_health',
        tone: 'sky',
        body: 'Détection rapide et confirmation exacte sont des moteurs différents. La sentinelle met en file tout ce qui dépasse deux fois sa ligne de base ; la couche de vérification recoupe par recherche en temps réel s’il s’agit d’un vrai événement. Et une couche distincte surveille, à chaque cycle, si l’ensemble est sain.',
        items: [
          { title: 'Sentinelle', body: 'Une couche de détection rapide à seuil bas, réglée pour ne rien manquer.', meta: 'sentinel' },
          { title: 'Couche de vérification', body: 'Confirme ce que la sentinelle remonte par recherche web en temps réel et consigne confirmé/rejeté.', meta: 'verification' },
          { title: 'Santé des sources', body: 'Compte si une valeur est réellement arrivée, non si la collecte a simplement tourné.', meta: 'source_health' },
          { title: 'Invariants de qualité', body: 'Attrape les cas où la source vit mais le calcul est cassé.', meta: 'quality_health · capability_ledger' },
        ],
      },
    ],
    cta: {
      title: 'La couche d’analyse et de réponse est dans Technologie II',
      body: 'Indice de risque par pays, prévisions à 7/14 jours, simulation de propagation sur 159 pays, scénarios d’intervention par alerte, criblage génomique et auto-vérification des prévisions suivent.',
      label: 'Voir Technologie II',
      href: 'technology-advanced',
    },
  },

  techSpec2: {
    metaTitle: 'Technologie II — analyse et réponse',
    metaDescription:
      'Indice de risque par pays, contrôle de la fatigue d’alerte, prévisions à 7/14 jours, cadre d’apprentissage nowcast, jumeau numérique de propagation sur 159 pays, estimation de la date d’importation, scénarios d’intervention par alerte, criblage génomique et évaluation/scellement des prévisions — la fiche technique et les moteurs de la couche d’analyse et de réponse d’AEGIRON.',
    eyebrow: 'TECHNOLOGY · II',
    title: 'Analyse et réponse',
    lead: 'Si la couche de veille trouve ce qui diffère, cette couche répond à où, combien et quoi faire. Elle quantifie le risque par pays, simule la propagation, compare les effets des interventions et évalue chacune de ses propres prévisions.',
    photo: {
      src: '/media/photos/avian-influenza-h5n1.jpg',
      alt: 'Micrographie électronique en transmission colorisée de particules du virus de la grippe aviaire A(H5N1)',
      caption: 'Particules du virus de la grippe aviaire A(H5N1), micrographie électronique en transmission colorisée. Document public des CDC américains.',
      credit: 'CDC / Cynthia Goldsmith · Domaine public',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:Colorized_transmission_electron_micrograph_of_Avian_influenza_A_H5N1_viruses.jpg',
    },
    blocks: [
      {
        title: 'Couche analyse et réponse — fiche technique',
        kicker: 'SPEC SHEET',
        tone: 'indigo',
        specs: [
          { label: 'Indice de risque par pays', value: 'Risque brut × vulnérabilité nationale (infrastructure · densité · connectivité aérienne · mouvements transfrontaliers)' },
          { label: 'Système d’alerte', value: 'Critique 90+ (3/j) · Élevée 80+ (5/j) · Moyenne 70+ · envoi Telegram en temps réel' },
          { label: 'Prévision de tendance', value: '7 jours · 14 jours — ensemble régression linéaire / lissage exponentiel' },
          { label: 'Jumeau numérique de propagation', value: 'SEIR métapopulationnel · 159 pays · 1 671 liaisons aériennes · 314 frontières terrestres' },
          { label: 'Paramètres de maladie', value: 'R0 · létalité mesurés dans la littérature pour 14 maladies' },
          { label: 'Criblage génomique', value: 'Statistiques de composition · naturel de l’ordre (Evo2) · couverture d’homologie (ColabFold)' },
          { label: 'Auto-vérification', value: 'Évaluation automatique (succès · Brier · calibration) · registre d’antériorité · scellement sur la chaîne Bitcoin' },
        ],
      },
      {
        title: 'Indice de risque par pays et contrôle de la fatigue d’alerte',
        kicker: 'ENGINE · country_risk · alerts · notifier',
        tone: 'crimson',
        body: 'Le risque final d’un pays est le risque brut issu des signaux multiplié par la vulnérabilité de la nation — un même signal devient un risque plus grand dans un pays à faible infrastructure sanitaire et à nombreuses liaisons internationales. Les alertes sont filtrées par niveau et plafond quotidien, pour que les destinataires ne reçoivent, immédiatement, que l’essentiel.',
        points: [
          'Les chiffres officiels (Corée, Brésil, Japon, Hong Kong) et les valeurs extraites des rapports sont combinés, pondérés par la fiabilité des sources.',
          'L’indice de vulnérabilité est rempli de valeurs mesurées issues d’indicateurs publics comme la Banque mondiale.',
          'Les alertes Critiques et Élevées sont poussées en une fois par Telegram, et les candidates au-delà du plafond sont conservées au dossier plutôt que supprimées.',
        ],
      },
      {
        title: 'Prévision et cadre d’apprentissage nowcast',
        kicker: 'ENGINE · forecast_engine · nowcast_*',
        tone: 'indigo',
        body: 'Les séries temporelles d’indicateurs sont extrapolées à 7 et 14 jours pour le briefing quotidien. À part, un cadre nowcast apprend « quel signal a mené à un vrai foyer ». Il assemble un jeu d’apprentissage à partir des déclarations officielles passées et du volume de presse de l’époque, évalue la performance uniquement sur des fenêtres futures non utilisées à l’entraînement, et laisse choisir l’équilibre entre rappel et taux de fausses alarmes.',
        items: [
          { title: 'Jeu d’apprentissage auto-assemblé', body: 'Accumule chaque jour étiquettes (déclarations officielles) et caractéristiques (volume de presse de l’époque).', meta: 'nowcast_dataset · nowcast_backfill' },
          { title: 'Évaluation prospective', body: 'Évalue sur un futur qu’il ne pouvait connaître, non sur les données d’entraînement.', meta: 'nowcast_eval' },
          { title: 'Choix du point de fonctionnement', body: 'Choisit entre rappel et taux de fausses alarmes le point voulu par l’organisation.', meta: 'nowcast_threshold' },
        ],
      },
      {
        title: 'Jumeau numérique de propagation et estimation d’importation',
        kicker: 'ENGINE · digital_twin · country_borders · global_inflow',
        tone: 'indigo',
        body: 'Un modèle SEIR métapopulationnel avec 159 pays comme nœuds, et 1 671 paires de pays reliées par avion et 314 frontières terrestres comme arêtes. À partir d’une origine et d’une maladie, il simule le moment et l’ampleur de l’arrivée par pays, et rapporte les pays qu’aucune voie n’atteint séparément de ceux pour lesquels il n’y a pas de données.',
        items: [
          { title: 'Propagation entre pays', body: 'Combine passagers aériens et mouvements terrestres pour ordonner les pays par arrivée.', meta: 'digital_twin · country_borders' },
          { title: 'Date d’importation nationale', body: 'À partir du trafic international de la ville d’origine, de la durée de vol et de la croissance initiale, estime les jours jusqu’à une première importation et le risque par point d’entrée.', meta: 'global_inflow · origin_catalog' },
          { title: 'Résolution infranationale', body: 'Ramène le risque national à l’échelle des unités administratives.', meta: 'geo_resolution' },
        ],
      },
      {
        title: 'Scénarios d’intervention par alerte',
        kicker: 'ENGINE · alert_intervention · defense · disease_params · decision_tree',
        tone: 'forest',
        body: 'Pour chaque nouvelle alerte critique ou élevée, une simulation SEIR de défense tourne avec des paramètres propres à la maladie et joint l’écart entre absence de réponse et intervention — en décès et en jours de saturation hospitalière. Une alerte ne s’arrête plus à « ce qui arrive » mais répond à « quelle mesure change quoi ».',
        points: [
          'Elle fait varier le début et l’intensité de l’isolement, de la distanciation et de la vaccination pour trouver la combinaison qui pousse le nombre de reproduction effectif sous 1.',
          'Le R0 et la létalité mesurés dans la littérature pour 14 maladies calibrent le modèle, et les résultats sont étiquetés « scénario de modèle ».',
          'Un arbre de décision fondé sur des règles génère instantanément des recommandations de réponse par niveau de risque.',
        ],
      },
      {
        title: 'Criblage génomique (HEIMDALL)',
        kicker: 'ENGINE · genome_signals · evo2_naturalness · msa_homology',
        tone: 'violet',
        body: 'Il lit une séquence sous trois angles différents. Les statistiques de composition regardent la composition des bases, Evo2 le naturel de l’ordre, et la recherche d’homologie si des protéines naturelles expliquent toute la séquence. C’est de la détection défensive uniquement, et son résultat est une priorité d’examen, non un verdict.',
        points: [
          'Les statistiques de composition (CAI, CpG) visent une composition non naturelle ; le naturel de l’ordre (Evo2) vise les segments assemblés ou recombinés.',
          'La recherche d’homologie est une interrogation de base publique, non un modèle entraîné, et fonctionne donc même sur des pathogènes qu’Evo2 ne peut traiter.',
          'Evo2 a exclu de son entraînement les virus à hôte eucaryote ; le domaine applicable est déclaré, et hors de celui-ci le score est rapporté sans signalement.',
        ],
        note: 'La fiche détaillée et la base par taxon sont exposées sous le programme spécial HEIMDALL.',
      },
      {
        title: 'Auto-vérification — évaluation et scellement',
        kicker: 'ENGINE · prediction_resolver · lead_time_ledger · prediction_timestamp',
        tone: 'teal',
        body: 'Pour prouver les prévisions comme un enregistrement, nous avons mis la vérification dans le code. Les prévisions enregistrées sont évaluées chaque jour au regard des déclarations officielles qui suivent, le moment où un signal a été vu pour la première fois est fixé avant toute déclaration, et chaque prévision est scellée au moment où elle est faite.',
        items: [
          { title: 'Évaluation automatique des prévisions', body: 'Les prévisions non résolues sont confrontées chaque jour aux déclarations officielles et classées en succès, échec ou indéterminé. Les pics de consultation et les mises à jour du nombre de cas ne servent pas de vérité terrain, pour ne pas évaluer nos signaux avec nos propres signaux.', meta: 'prediction_resolver · prediction_scoring' },
          { title: 'Registre d’antériorité', body: 'Consigne le moment où un signal a été vu pour la première fois, avant toute déclaration officielle. Une antériorité reconstituée après coup n’est pas acceptée comme mesure.', meta: 'lead_time_ledger' },
          { title: 'Scellement des prévisions', body: 'L’empreinte SHA-256 d’une prévision est ancrée à la chaîne Bitcoin via OpenTimestamps. Un tiers peut vérifier lui-même qu’elle n’a pas été réécrite ensuite.', meta: 'prediction_timestamp' },
        ],
      },
    ],
    cta: {
      title: 'Deux couches, une seule chaîne',
      body: 'Détecter → juger → prévoir → simuler → prescrire → auto-vérifier → sceller. L’écran où cette chaîne tourne réellement est le tableau de bord en direct.',
      label: 'Tableau de bord en direct',
      href: '/dashboard',
    },
  },

  engines: {
    metaTitle: 'Catalogue des moteurs — la carte complète des 116 modules',
    metaDescription:
      'Les 116 modules algorithmiques d’AEGIRON, regroupés en sept : veille, extraction, jugement, prévision, génomique, contre-mesures et vérification. Ce que fait chaque module, et s’il tourne chaque heure ou à la demande.',
    eyebrow: 'ENGINE CATALOGUE',
    title: '116 modules, sept systèmes',
    lead: 'AEGIRON n’est pas un grand modèle unique mais 116 modules, chacun faisant une chose bien, imbriqués — car surveiller le monde entier demande autant d’angles. Les modules principaux sont organisés en sept systèmes nommés — HUGINN, MIMIR, FORSETI, SKULD, HEIMDALL, VALHALLA et VAR — la couche moteurs du système phare d’AEGIRON (voir BAIKAL MOB).',
    blocks: [
      {
        title: 'HUGINN — Veille — rassembler les signaux, trouver les anomalies',
        kicker: 'SYSTEM 01 · HUGINN',
        tone: 'teal',
        items: [
          { title: 'Veille de la presse locale', body: 'Sélectionne les articles de foyer dans l’actualité agrégée de 178 pays et 52 langues.', meta: 'local_news · horaire' },
          { title: 'Indice d’anomalie à six couches', body: 'Combine six couches de signaux, scorés contre leur niveau habituel, en un indice.', meta: 'gai · horaire' },
          { title: 'Veille des silences', body: 'Traite un canal actif qui se tait comme un signal.', meta: 'negative_space · horaire' },
          { title: 'Foyers inexpliqués', body: 'Compte les foyers qu’aucune maladie connue n’explique.', meta: 'unexplained · horaire' },
          { title: 'Rapport unique à haut risque', body: 'Remonte sur un seul rapport les pathogènes dont un événement fait l’actualité — peste, anthrax.', meta: 'pathogen_sentinel · horaire' },
          { title: 'Détection standard', body: 'Attrape les anomalies avec CDC EARS C1/C2/C3 et une ligne de base z-score.', meta: 'ears · anomaly_engine · kdca_anomaly' },
          { title: 'Détection à deux étages', body: 'Une sentinelle rapide remonte ; une couche de vérification recoupe.', meta: 'sentinel · verification' },
          { title: 'Catastrophe · polaire · climat', body: 'Lit les signaux environnementaux de conditions changeantes comme indicateurs précurseurs.', meta: 'disaster_watch · polar_* · climate_signals' },
          { title: 'Commerce · appels d’offres · animal', body: 'Suit importations de fournitures médicales, appels d’offres publics et épizooties.', meta: 'comtrade_signals · procurement_watch · wahis' },
        ],
      },
      {
        title: 'MIMIR — Extraction — transformer textes et tableaux en chiffres',
        kicker: 'SYSTEM 02 · MIMIR',
        tone: 'sky',
        items: [
          { title: 'Extraction de tableaux PDF', body: 'Restitue les tableaux des rapports de santé en structure lignes-colonnes.', meta: 'pdf_table_extract' },
          { title: 'Signalisation · chargement', body: 'Convertit les tableaux restitués en signaux normalisés, les charge et dérive des tendances.', meta: 'bulletin_signals · bulletin_ingest · bulletin_trend' },
          { title: 'Extraction NLP de signaux', body: 'Transforme la presse en texte libre en JSON structuré pour l’agrégation.', meta: 'nlp_extract' },
          { title: 'Résolution des pays', body: 'Résout des lieux en texte libre en listes de codes pays ISO.', meta: 'country_resolve · geo_resolution' },
          { title: 'Déduplication d’événements', body: 'Regroupe le même événement de plusieurs sources en un seul pour éviter les alertes en double.', meta: 'event_dedup' },
          { title: 'Couche modèle d’extraction', body: 'Permet de basculer le chemin d’extraction en un seul endroit vers un modèle propriétaire.', meta: 'aegiron_model · nvidia' },
        ],
      },
      {
        title: 'FORSETI — Jugement — décider s’il faut lever une alerte',
        kicker: 'SYSTEM 03 · FORSETI',
        tone: 'crimson',
        items: [
          { title: 'Indice de risque par pays', body: 'Multiplie le risque brut par la vulnérabilité nationale pour un risque final.', meta: 'country_risk · country_indicators' },
          { title: 'Contrôle de la fatigue d’alerte', body: 'Ne garde que les alertes qui méritent l’attention, par niveau et plafond quotidien.', meta: 'alerts' },
          { title: 'Notification en temps réel', body: 'Pousse les alertes Critiques et Élevées par Telegram en une fois.', meta: 'notifier' },
          { title: 'Moteur de fiabilité', body: 'Pèse rumeur et estimation différemment des données primaires officielles.', meta: 'trust' },
          { title: 'Quantification du risque', body: 'Produit des indicateurs relatifs comparables pour l’assurance et la finance.', meta: 'risk_quantification' },
        ],
      },
      {
        title: 'SKULD — Prévision · simulation — voir où cela se propagera',
        kicker: 'SYSTEM 04 · SKULD',
        tone: 'indigo',
        items: [
          { title: 'Prévision à 7/14 jours', body: 'Extrapole les séries d’indicateurs par un ensemble.', meta: 'forecast_engine' },
          { title: 'Jumeau numérique de propagation', body: 'Simulation SEIR sur un réseau aérien et terrestre de 159 pays.', meta: 'digital_twin · country_borders' },
          { title: 'Date d’importation nationale', body: 'Estime les jours jusqu’à une première importation depuis l’origine.', meta: 'global_inflow · origin_catalog' },
          { title: 'Apprentissage nowcast', body: 'Assemble des jeux signal→foyer et évalue de façon prospective.', meta: 'nowcast_dataset · nowcast_eval' },
          { title: 'Graphe de connaissances', body: 'Interprète les signaux par des chaînes de cause à effet.', meta: 'knowledge_graph' },
          { title: 'Rapport hebdomadaire d’importation', body: 'Anomalie par pays × vols directs vers la Corée, une page par semaine ISO. L’indice d’exposition n’est pas une probabilité.', meta: 'korea_import_report' },
        ],
      },
      {
        title: 'HEIMDALL — Génomique — lire les séquences de façon défensive',
        kicker: 'SYSTEM 05 · HEIMDALL',
        tone: 'violet',
        items: [
          { title: 'Statistiques de composition', body: 'Regarde une composition non naturelle avec CAI, CpG et autres.', meta: 'genome_signals' },
          { title: 'Naturel de l’ordre', body: 'Mesure le naturel de l’ordre de la séquence avec Evo2.', meta: 'evo2_naturalness' },
          { title: 'Détection de chimères par homologie', body: 'Cherche si des protéines naturelles couvrent toute la séquence.', meta: 'msa_homology' },
          { title: 'Suivi des lignées', body: 'Lit le changement de lignée dominante par réanalyse Nextstrain.', meta: 'genomic_variants' },
        ],
      },
      {
        title: 'VALHALLA — Contre-mesures — compter ce qui peut l’arrêter (VALHALLA)',
        kicker: 'SYSTEM 06 · VALHALLA',
        tone: 'forest',
        items: [
          { title: 'Écart de couverture', body: 'Quelles menaces le stock actuel et les produits approuvés ne couvrent pas.', meta: 'countermeasure_stockpile · approved_products' },
          { title: 'Souveraineté de production', body: '« Combien de lieux peuvent le fabriquer », d’après la liste de l’OMS.', meta: 'vaccine_supply · countermeasure_pipeline' },
          { title: 'Périmètres de préparation', body: 'Répond à la préparation par périmètre — stock national ou offre mondiale.', meta: 'readiness_scopes · ihr_capacity' },
          { title: 'Scénarios d’intervention', body: 'Simule par alerte l’écart entre absence de réponse et intervention.', meta: 'alert_intervention · defense' },
          { title: 'Veille Valhalla', body: 'Accumule chaque jour la préparation en contre-mesures pour voir la tendance.', meta: 'valhalla_watch' },
        ],
      },
      {
        title: 'VAR — Vérification — nous contrôlons nos propres chiffres',
        kicker: 'SYSTEM 07 · VAR',
        tone: 'teal',
        items: [
          { title: 'Évaluation automatique des prévisions', body: 'Classe les prévisions face aux déclarations officielles en succès, échec ou attente.', meta: 'prediction_resolver · prediction_scoring' },
          { title: 'Registre d’antériorité', body: 'Fixe le moment où un signal a été vu avant toute déclaration.', meta: 'lead_time_ledger' },
          { title: 'Scellement des prévisions', body: 'Ancre l’empreinte d’une prévision à la chaîne Bitcoin.', meta: 'prediction_timestamp' },
          { title: 'Prévisions de tendance hebdomadaires', body: 'Scelle et évalue automatiquement les paris hausse/baisse de la semaine suivante sur la surveillance hebdomadaire officielle du Japon, dans un tableau séparé des prévisions à 90 jours.', meta: 'weekly_forecast' },
          { title: 'Santé des sources', body: 'Compte à chaque cycle si une valeur est réellement arrivée.', meta: 'source_health' },
          { title: 'Invariants de qualité', body: 'Attrape un calcul cassé même quand la source vit.', meta: 'quality_health · capability_ledger' },
          { title: 'Préparation au lancement', body: 'Répond à « sommes-nous prêts à lancer » par une mesure, non une opinion.', meta: 'launch_readiness' },
        ],
      },
    ],
    cta: {
      title: 'Voyez les valeurs que ces moteurs produisent réellement',
      body: 'Le tableau de bord montre les signaux et indicateurs que ces modules génèrent en ce moment.',
      label: 'Ouvrir le tableau de bord',
      href: '/dashboard',
    },
  },

  programs: {
    metaTitle: 'Programmes spéciaux — HEIMDALL · VALHALLA',
    metaDescription:
      'Les deux programmes de R&D internes d’AEGIRON. HEIMDALL traite le criblage génomique défensif ; VALHALLA, la préparation en contre-mesures. Tous deux opèrent dans une limite d’honnêteté énoncée, sans surévaluer leurs capacités.',
    eyebrow: 'SPECIAL PROGRAMS',
    title: 'HEIMDALL · VALHALLA',
    lead: 'La plupart des couches de veille opèrent à découvert. Mais deux axes sont d’une nature différente — le criblage génomique des menaces biologiques et la préparation nationale en contre-mesures. Parce qu’ils sont sensibles, nous en gérons la responsabilité et l’accès à part ; cette page énonce seulement ce qu’ils font et ne font pas, sans rien surévaluer.',
    photo: {
      src: '/media/photos/ebola-virion.jpg',
      alt: 'Micrographie électronique en transmission colorisée d’une particule du virus Ebola',
      caption: 'Particule du virus Ebola, micrographie électronique en transmission colorisée. Document public des CDC américains — non des données de laboratoire d’AEGIRON.',
      credit: 'CDC / Cynthia Goldsmith · Domaine public',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:Ebola_virus_virion.jpg',
    },
    blocks: [
      {
        title: 'HEIMDALL — criblage génomique défensif',
        kicker: 'PROGRAM · HEIMDALL',
        tone: 'violet',
        deep: true,
        body: 'Nommé d’après le gardien qui veille sur le pont dans la mythologie nordique. C’est la fonction défensive du criblage de biosécurité — détecter et signaler si une séquence génomique donnée présente des signaux s’écartant des statistiques de l’évolution naturelle. Il examine ensemble les statistiques de composition, le naturel de l’ordre et la couverture d’homologie (la couche génomique de Technologie II).',
        points: [
          '**Détection défensive uniquement.** Il ne conçoit, ne synthétise ni n’optimise de séquences, et ne fournit aucun moyen de contourner le criblage.',
          'Le résultat est une « priorité d’examen approfondi », non un verdict. Un jugement final requiert un expert et un travail de paillasse (is_screening_only).',
          'Bactéries, archées, génomes eucaryotes et phages sont dans le domaine applicable. Les virus à hôte eucaryote en sortent par une limite de modèle, et ce fait est indiqué dans la réponse.',
        ],
        note: 'Le point d’accès exige une authentification et chaque accès est consigné dans un journal d’audit. Relever le niveau de sécurité ne relève pas les affirmations — classifié signifie contrôle d’accès, non traiter le non validé comme validé.',
      },
      {
        title: 'VALHALLA — préparation en contre-mesures',
        kicker: 'PROGRAM · VALHALLA',
        tone: 'forest',
        deep: true,
        body: 'Plutôt que d’imiter une prédiction de neutralisation au niveau moléculaire, il répond aux questions que l’on peut réellement défendre — quelles menaces notre stock ne peut couvrir (l’écart de couverture) et, parmi celles qu’il couvre, lesquelles ne peuvent être produites sur le territoire (l’écart de souveraineté de production). Ce sont les questions centrales de la planification nationale de biosécurité, et tout est calculé à partir de données publiques.',
        items: [
          { title: 'Écart de couverture', body: 'Quelles maladies disposent d’un stock d’urgence international ou d’un produit approuvé par la réglementation. Nous ne touchons pas aux informations non publiques comme les quantités des stocks nationaux.', meta: 'Sources publiques : OMS ICG, openFDA, etc.' },
          { title: 'Souveraineté de production', body: 'À partir de la liste de préqualification de l’OMS, combien de lieux dans le monde peuvent fabriquer un produit donné. Sur 56 produits, 17 n’ont qu’un seul fabricant — un goulot d’étranglement que cela met au jour.', meta: 'Un point unique d’approvisionnement = le risque qu’un stock ne puisse être reconstitué' },
          { title: 'Stade de développement', body: 'Via ClinicalTrials.gov, il décompose « encore en développement » jusqu’à la phase d’essai, séparant les états regroupés sous « pas de stock » (phase 3 en cours vs aucune phase indiquée).', meta: 'La distinction qui fixe la priorité de préparation' },
        ],
      },
      {
        title: 'La limite d’honnêteté',
        accent: true,
        body: 'Les deux programmes prennent pour règle de fonctionnement de ne pas surévaluer leurs capacités. La limite est fixée dans les commentaires du code, et la réponse la transporte avec elle.',
        points: [
          'HEIMDALL reste une **priorité de criblage, non un verdict.**',
          'L’efficacité de VALHALLA est un **agrégat de l’efficacité déclarée (étiquette) de chaque contre-mesure**, non une prédiction de neutralisation moléculaire.',
          'Là où les données manquent, il ne les invente pas et laisse prudemment la couverture « inconnue ».',
        ],
        note: 'Les noms de code des programmes et la structure organisationnelle sont des définitions internes propres à AEGIRON, non une affiliation à un organisme gouvernemental ni une classification de sécurité officielle.',
      },
    ],
    cta: {
      title: 'Ce que mesurent réellement les moteurs de génomique et de propagation',
      body: 'Les mesures par taxon de la couche génomique et les limites de réseau de la simulation sont exposées dans Technologie II.',
      label: 'Voir Technologie II',
      href: 'technology-advanced',
    },
  },


  transparency: {
    metaTitle: 'Validation et limites — comment le système se vérifie lui-même',
    metaDescription:
      'Comment AEGIRON a intégré la vérification dans le système, avec ses limites connues et ses lacunes de données — les mécanismes qui empêchent un chiffre d’aller plus loin que sa preuve.',
    eyebrow: 'VALIDATION & LIMITS',
    title: 'Validation et limites',
    lead: 'Le plus dangereux dans la veille épidémiologique n’est pas une prévision fausse, mais une prévision invérifiable. AEGIRON a donc intégré la vérification dans le code. Voici comment le système contrôle ses propres chiffres, avec ses limites connues.',
    blocks: [
      {
        title: 'La vérification que le système opère lui-même',
        kicker: 'SELF-CHECK',
        tone: 'teal',
        body: 'Si les limites ne sont écrites que dans des documents, les chiffres s’en détachent et sont réutilisés tels quels à l’écran et dans les rapports. La vérification est donc dans le code.',
        points: [
          '**Comparaison historique** — les estimations de décès modélisées sont comparées automatiquement à la plus grande épidémie connue pour cette maladie ; bien au-delà de cet intervalle, un avertissement « ne pas utiliser en externe » accompagne la réponse.',
          '**Séparer les causes d’échec** — quand un foyer est manqué, « le modèle l’a manqué » est distingué de « il n’y avait pas de donnée pour le voir ». Les confondre inverse le diagnostic.',
          '**Évaluation prospective** — la performance est évaluée uniquement sur un futur inconnaissable à l’époque, jamais sur les données d’entraînement.',
          '**Provenance** — quand un nom de maladie ou de pays vient du contexte et non d’un tableau, son origine est consignée à côté.',
        ],
      },
      {
        title: 'Comment les prévisions sont prouvées comme enregistrement',
        kicker: 'PROOF',
        tone: 'indigo',
        body: 'La prétention de « savoir avant les autres » n’a de sens que s’il existe un moyen de la prouver. AEGIRON scelle chaque prévision au moment où elle est faite et l’évalue chaque jour au regard des déclarations officielles qui suivent. L’historique se bâtit à partir de cet enregistrement scellé, non d’une affirmation.',
        points: [
          'L’empreinte d’une prévision est ancrée à la chaîne Bitcoin, et ne peut donc être réécrite après coup.',
          'Le moment où un signal a été vu pour la première fois est fixé avant toute déclaration officielle, de sorte que l’antériorité ne compte qu’en temps réel.',
          'Les pics de consultation et les mises à jour du nombre de cas ne servent pas de vérité terrain, pour ne pas évaluer nos signaux avec eux-mêmes.',
        ],
      },
      {
        title: 'Limites connues',
        kicker: 'KNOWN LIMITS',
        tone: 'amber',
        items: [
          { title: 'Lacunes de collecte', body: 'Des signaux peuvent manquer pour certains pays et certaines périodes. Le système indique lui-même quels intervalles sont vides.', meta: 'Les lacunes sont montrées, non cachées' },
          { title: 'Seuils d’alerte', body: 'La sensibilité d’une alerte est une politique d’exploitation, non une réponse technique. Nous n’avançons pas un unique seuil « correct ».', meta: 'Un point de fonctionnement que l’organisation choisit' },
          { title: 'Extraction par machine', body: 'L’extraction des tableaux PDF peut mal lire ; un recoupement avec la source est appliqué et les valeurs non confirmées sont signalées à part.', meta: 'Les valeurs non vérifiées sont marquées' },
          { title: 'Traitement en langue locale', body: 'Au lieu de la traduction automatique, un classifieur à modèle de langage et l’appariement par mots-clés sont utilisés — un choix pour éviter que des noms de maladie ne disparaissent ou ne s’inversent à la traduction.', meta: 'Un choix de conception pour la précision' },
        ],
      },
      {
        title: 'Pourquoi nous divulguons nos limites d’abord',
        body: 'AEGIRON n’est lié par aucun contrat client à préserver, et peut donc divulguer ses limites en premier — ce qui devient une base de confiance que la diligence peut vérifier directement. La première chose que vérifient réassureurs et évaluateurs publics, c’est si une organisation connaît précisément ses propres limites.',
      },
    ],
    cta: {
      title: 'Si vous trouvez une erreur',
      body: 'Si quelque chose sur cette page est inexact, ou si une limite manque, dites-le-nous. Nous le vérifierons et le refléterons.',
      label: 'Nous contacter',
      href: 'contact',
    },
  },

  dataSources: {
    metaTitle: 'Sources de données — les 23 sources opérationnelles, intégralement',
    metaDescription:
      'Les 23 sources de données qu’AEGIRON collecte chaque heure, par catégorie — ce que chacune montre, ce qu’elle ne peut montrer et la fréquence de mise à jour de sa source d’origine.',
    eyebrow: 'DATA SOURCES',
    title: '23 sources de données',
    lead: 'Un jugement dont les fondements sont cachés ne peut être vérifié. Toutes les sources de collecte opérationnelles sont donc listées ici par catégorie, sans exception, avec ce que chacune ne peut pas voir.',
    blocks: [
      {
        title: 'Autorités sanitaires officielles',
        kicker: 'OFFICIAL',
        tone: 'teal',
        body: 'Les plus fiables et les plus lentes, car elles passent par une confirmation officielle. En alerte précoce, elles servent de référence pour pondérer les autres signaux.',
        items: [
          { title: 'Bureau régional de l’OMS pour l’Afrique', body: 'Avis d’épidémie et rapports de situation pour la région africaine.', meta: 'Mise à jour à la source : au fil de l’eau' },
          { title: 'Bureau régional de l’OMS pour les Amériques (OPS)', body: 'Alertes et mises à jour épidémiologiques pour les Amériques.', meta: 'Mise à jour à la source : au fil de l’eau' },
          { title: 'Agence coréenne de contrôle et de prévention des maladies', body: 'Déclarations hebdomadaires des 45 maladies infectieuses à déclaration obligatoire en Corée.', meta: 'Mise à jour à la source : hebdomadaire' },
          { title: 'Bulletin hebdomadaire japonais (IDWR)', body: 'Surveillance sentinelle hebdomadaire de l’Institut national japonais des maladies infectieuses.', meta: 'Mise à jour à la source : hebdomadaire' },
          { title: 'Centre de protection de la santé de Hong Kong', body: 'Avis de surveillance des maladies transmissibles et rapports réguliers sur la grippe aviaire.', meta: 'Mise à jour à la source : au fil de l’eau' },
          { title: 'InfoDengue (Brésil)', body: 'Nombre de reproduction effectif de la dengue et niveaux d’alerte, à l’échelle des villes.', meta: 'Mise à jour à la source : hebdomadaire' },
        ],
      },
      {
        title: 'Sources académiques et spécialisées',
        kicker: 'ACADEMIC',
        tone: 'sky',
        body: 'Elles peuvent précéder les annonces officielles, mais fluctuent au rythme des cycles de recherche et de publication. Seules, elles ne relèvent jamais un niveau d’alerte ; elles ne pèsent que lorsqu’elles coïncident avec d’autres couches.',
        items: [
          { title: 'CDC Emerging Infectious Diseases', body: 'La revue des CDC américains consacrée aux maladies infectieuses émergentes.', meta: 'Mise à jour à la source : à la publication' },
          { title: 'CIDRAP', body: 'Informations par maladie du Center for Infectious Disease Research and Policy de l’Université du Minnesota.', meta: 'Mise à jour à la source : à la publication' },
          { title: 'PubMed', body: 'Évolution du nombre d’articles sur des pathogènes donnés.', meta: 'Mise à jour à la source : quotidienne' },
          { title: 'medRxiv', body: 'Nombre de prépublications médicales déposées avant évaluation par les pairs.', meta: 'Mise à jour à la source : quotidienne' },
        ],
      },
      {
        title: 'Presse et attention du public',
        kicker: 'REPORTING',
        tone: 'crimson',
        body: 'Les plus rapides et les plus bruitées. L’actualité ne bouge qu’après qu’un journaliste a écrit son article ; ces sources reçoivent donc une fiabilité faible et sont toujours lues au regard d’autres axes.',
        items: [
          { title: 'Presse en langue locale', body: 'Flux d’actualité agrégés pour 178 pays en 52 langues (179 flux) ; les flux ambigus sont reclassés par un modèle de langage.', meta: 'Mise à jour à la source : horaire' },
          { title: 'NewsWatch', body: 'Tendances de l’actualité des grandes maladies infectieuses, lues dans des résultats de recherche web résumés.', meta: 'Mise à jour à la source : horaire' },
          { title: 'Tendances de recherche Naver', body: 'Ratios de recherche sur la grippe, la COVID-19 et Ebola en Corée.', meta: 'Mise à jour à la source : quotidienne' },
          { title: 'Mastodon', body: 'Nombre de personnes publiant sous des mots-clics liés à des maladies (fenêtre glissante de sept jours).', meta: 'Mise à jour à la source : horaire' },
          { title: 'Consultations Wikipédia', body: 'Consultations des articles liés à Ebola. La source est actuellement instable ; les valeurs n’arrivent que par intermittence.', meta: 'Mise à jour à la source : quotidienne · instable' },
          { title: 'Polymarket', body: 'Prix de marchés prédictifs sur une nouvelle pandémie — un jugement collectif, non une preuve.', meta: 'Mise à jour à la source : horaire' },
        ],
      },
      {
        title: 'Environnement, animaux et comportements de préparation',
        kicker: 'ENVIRONMENT',
        tone: 'forest',
        body: 'Ces sources observent les conditions d’une épidémie et les comportements de préparation plutôt que l’épidémie elle-même. Ce ne sont pas des preuves directes, mais elles peuvent bouger en premier quand les autres axes restent calmes.',
        items: [
          { title: 'Surveillance des eaux usées (CDC NWSS)', body: 'Concentrations de pathogènes dans les stations d’épuration américaines — un signal antérieur à l’apparition des symptômes.', meta: 'Mise à jour à la source : hebdomadaire' },
          { title: 'Maladies animales WAHIS', body: 'Déclarations de foyers animaux de l’Organisation mondiale de la santé animale — le stade animal des zoonoses.', meta: 'Mise à jour à la source : au fil de l’eau' },
          { title: 'Fenêtre de veille post-catastrophe (GDACS)', body: 'Après une inondation, un séisme ou un cyclone, le pays touché est surveillé avec un seuil abaissé tant que le risque infectieux est élevé.', meta: 'Mise à jour à la source : au fil de l’eau' },
          { title: 'Observation polaire', body: 'Signaux liés au dégel du pergélisol et à la grippe aviaire dans les régions polaires — une couche d’observation, non d’alerte.', meta: 'Mise à jour à la source : quotidienne' },
          { title: 'Signaux de chaîne d’approvisionnement', body: 'Tendances de recherche liées à la demande de médicaments tels qu’antipyrétiques et masques.', meta: 'Mise à jour à la source : quotidienne' },
        ],
      },
      {
        title: 'Génomique et contre-mesures',
        kicker: 'GENOMICS',
        tone: 'violet',
        items: [
          { title: 'Suivi des lignées Nextstrain', body: 'Composition des lignées dominantes et apparition de nouvelles lignées dans les séquences publiques réanalysées. Les jeux de données qui ne sont plus mis à jour ne sont pas utilisés.', meta: 'Mise à jour à la source : variable selon le jeu' },
          { title: 'Données de contre-mesures VALHALLA', body: 'Documents publics sur la préparation en contre-mesures : liste de préqualification de l’OMS, ClinicalTrials.gov et avis de marchés publics coréens (KONEPS).', meta: 'Mise à jour à la source : quotidienne et mensuelle' },
        ],
        note: 'Selon le contrôle opérationnel de santé des sources du 2026-10-18. Le nombre de sources saines en ce moment est affiché en direct par le badge d’état de la page d’accueil.',
      },
    ],
    cta: {
      title: 'Vérifiez l’état actuel de chaque source',
      body: 'Le tableau de bord montre le dernier état de collecte de chaque source et les indicateurs que produisent ses signaux.',
      label: 'Ouvrir le tableau de bord',
      href: '/dashboard',
    },
  },

  methodology: {
    metaTitle: 'Méthodologie — une structure en quatre couches',
    metaDescription:
      'La méthodologie d’AEGIRON en quatre couches — collecte, extraction, analyse et prévision : des méthodes académiques établies, intégrées dans un produit opérationnel.',
    eyebrow: 'METHODOLOGY',
    title: 'Une méthodologie en quatre couches',
    lead: 'Nous n’avons pas inventé de nouvelles mathématiques. Nous avons intégré des méthodes déjà établies en épidémiologie des maladies infectieuses et en épidémiologie de surveillance dans un produit qui tourne automatiquement chaque jour — et nous indiquons le standard que suit chaque couche.',
    blocks: [
      {
        kicker: 'LAYER 01',
        tone: 'teal',
        title: 'Couche 1 · Collecte',
        body: 'Vingt-trois sources de collecte de natures très différentes sont normalisées dans un format de signal unique. La fiabilité variant selon l’origine, chaque valeur est conservée avec sa fiabilité, utilisée comme pondération dans tous les calculs ultérieurs.',
      },
      {
        kicker: 'LAYER 02',
        tone: 'sky',
        title: 'Couche 2 · Extraction',
        body: 'Des chiffres structurés sont extraits de documents non structurés (tableaux PDF et texte d’articles). Les images de documents sont interprétées bloc par bloc, et les chiffres extraits sont confrontés au texte source. Les valeurs qui ne peuvent y être confirmées sont marquées comme non vérifiées.',
      },
      {
        kicker: 'LAYER 03',
        tone: 'crimson',
        title: 'Couche 3 · Analyse',
        body: 'Elle suit les standards de l’épidémiologie de surveillance. Les anomalies sont jugées par des z-scores au regard de la ligne de base de chaque pays et par des méthodes de la famille CDC EARS ; la performance est évaluée par la sensibilité, la spécificité, la valeur prédictive positive et le taux de fausses alertes.',
        points: [
          'Sensibilité (POD) = part des épidémies réelles détectées',
          'Spécificité = part des périodes normales jugées normales',
          'Taux de fausses alertes (FAR) = part des alertes qui étaient fausses',
          'Le bon taux de fausses alertes relève de la **politique opérationnelle,** non d’une question technique. Le nombre d’alertes que des personnes peuvent examiner par jour, et le rapport entre le coût d’un manque et celui d’une fausse alerte, sont fixés par l’organisation. Nous ne mettons donc pas en avant un seuil « juste » unique.',
        ],
      },
      {
        kicker: 'LAYER 04',
        tone: 'indigo',
        title: 'Couche 4 · Prévision',
        body: 'Les voies de propagation sont estimées avec un modèle compartimental SEIR standard auquel s’ajoutent des interventions variables dans le temps. Les paramètres propres à chaque maladie proviennent de mesures publiées.',
        points: [
          'Pour les pathogènes à transmission par contact limitée, la **population atteignable** est restreinte. Appliquer le R0 de 1,8 d’Ebola à une population entière donne 87 fois la plus grande épidémie connue — c’est réellement arrivé, et nous l’avons corrigé.',
          'L’effet d’une intervention est jugé selon que le nombre de reproduction effectif passe ou non sous 1.',
          'Chaque résultat est présenté comme un « scénario de modèle », accompagné de la comparaison historique.',
        ],
      },
      {
        title: 'La place de cette méthodologie',
        body: 'La modélisation des maladies infectieuses combinant prévision et simulation est pratiquée depuis plus de dix ans par des équipes comme le MRC GIDA de l’Imperial College et le MOBS Lab de Northeastern. Ce qu’AEGIRON a construit n’est pas une méthode, mais **la structure qui fait tourner ces méthodes automatiquement chaque jour, sous forme de produit commercial.** Nous ne prétendons pas être les premiers au monde.',
      },
    ],
  },

  solutionsReinsurance: {
    metaTitle: 'Pour la réassurance et l’assurance',
    metaDescription:
      'Indices d’exposition par pays et comparaison de portefeuille. Chaque réponse précise qu’il s’agit d’indicateurs relatifs, non de probabilités absolues.',
    eyebrow: 'FOR REINSURANCE',
    title: 'Réassurance et assurance',
    lead: 'La place où le risque pandémique était quantifié est vacante. Ce que nous fournissons, toutefois, ce sont des indicateurs relatifs et non des probabilités — et cette distinction est imposée dans chaque réponse.',
    blocks: [
      {
        title: 'Ce que nous fournissons',
        tone: 'indigo',
        items: [
          { title: 'Indice d’exposition par pays', body: 'Un indice de 0 à 100 combinant pression des signaux, vulnérabilité et potentiel de propagation, pour comparer et classer les pays.' },
          { title: 'Comparaison de portefeuille', body: 'Les pays que vous détenez, sur un seul écran, par percentile relatif.' },
          { title: 'Contrefactuels d’intervention', body: 'Comparaison, par modèle, des scénarios d’intervention avec l’absence de réponse.' },
          { title: 'Registre de prévisions scellées', body: 'Les prévisions sont scellées à leur création : un historique vérifiable se constitue au fil du temps.' },
        ],
      },
      {
        title: 'Ce que vous devez savoir',
        accent: true,
        points: [
          'L’indice d’exposition **n’est pas une probabilité absolue.** Chaque réponse porte `is_probability: false`.',
          'Les pondérations sont des valeurs de politique, non des valeurs calibrées empiriquement — indiqué par `weights_calibrated: false`.',
          'Il n’existe pas encore d’historique de prévisions validé. L’outil n’est pas prêt à être utilisé directement dans la tarification.',
        ],
      },
    ],
    cta: {
      title: 'Vous pouvez commencer par la due diligence',
      body: 'L’ensemble du système est ouvert. Vérifiez-le d’abord, puis discutons du périmètre d’adoption.',
      label: 'Nous contacter',
      href: 'contact',
    },
  },

  solutionsGovernment: {
    metaTitle: 'Pour les gouvernements et la santé publique',
    metaDescription:
      'Suivi des voies d’importation et comparaison de scénarios d’intervention — l’effet de chaque mesure de défense, comparé par modèle.',
    eyebrow: 'FOR GOVERNMENT',
    title: 'Gouvernements et santé publique',
    lead: 'Nous examinons à la fois les voies par lesquelles une épidémie à l’étranger entre sur le territoire et les mesures qui maîtrisent réellement la transmission.',
    blocks: [
      {
        title: 'Ce que nous fournissons',
        tone: 'forest',
        items: [
          { title: 'Suivi des voies d’importation', body: 'Voies de risque d’importation estimées à partir de la connectivité aérienne et de pondérations à l’échelle des villes.' },
          { title: 'Comparaison de scénarios d’intervention', body: 'Des combinaisons d’isolement, de distanciation, de vaccination et de traitement sont testées pour trouver la plus petite qui fait passer le nombre de reproduction effectif sous 1.' },
          { title: 'Estimation de la charge hospitalière', body: 'Jours de saturation hospitalière estimés à partir de la courbe épidémique.' },
          { title: 'Bulletins quotidiens', body: 'Une synthèse de situation générée automatiquement chaque jour. Les jours calmes, elle dit que la journée était calme.' },
        ],
      },
      {
        title: 'Ce que vous devez savoir',
        accent: true,
        points: [
          'Les chiffres de scénario sont des **estimations sous hypothèses de modèle.** Un examen par un épidémiologiste est nécessaire avant de les utiliser comme fondement de politique.',
          'Le système joint lui-même un avertissement aux valeurs situées hors de l’intervalle expliqué par la comparaison historique.',
        ],
      },
    ],
    cta: {
      title: 'Tout ce qu’il faut pour une évaluation est public',
      body: 'Examinez d’abord le système, la méthodologie et les limites, puis discutons du périmètre d’un pilote.',
      label: 'Nous contacter',
      href: 'contact',
    },
  },

  solutionsNgo: {
    metaTitle: 'Pour les organisations multilatérales et humanitaires',
    metaDescription:
      'Des signaux précoces dans les régions à surveillance faible — y compris des pays que d’autres couvrent rarement faute d’intérêt commercial.',
    eyebrow: 'FOR MULTILATERAL & HUMANITARIAN',
    title: 'Multilatéral et humanitaire',
    lead: 'Plus la surveillance est faible, plus le signal arrive tard. AEGIRON a intégré dès le départ dans son périmètre précisément les régions que les services existants couvrent rarement, faute d’incitation commerciale.',
    blocks: [
      {
        title: 'Ce que nous fournissons',
        tone: 'teal',
        items: [
          { title: 'Priorité aux régions vulnérables', body: 'Inclut des pays aux lacunes de surveillance importantes, comme le Nigeria, l’Éthiopie, le Yémen, Madagascar et la Papouasie-Nouvelle-Guinée.' },
          { title: 'Premiers articles en langue locale', body: 'La couverture locale avant que la presse internationale ne s’empare d’un événement.' },
          { title: 'Détection d’événements inexpliqués', body: 'Les foyers qu’aucune maladie connue n’explique sont signalés à part.' },
          { title: 'Signalement des lacunes de collecte', body: 'Le système indique lui-même quelles régions et périodes sont vides — une information dont le terrain a besoin en soi.' },
        ],
      },
      {
        title: 'Ce que vous devez savoir',
        accent: true,
        points: [
          'Plus la surveillance d’une région est faible, **plus nos propres données risquent d’être vides elles aussi.** Les lacunes sont montrées, non masquées.',
          'Le traitement des langues locales repose sur des mots-clés plutôt que sur la traduction automatique, celle-ci ayant échoué à notre validation de qualité.',
        ],
      },
    ],
    cta: {
      title: 'Nous recherchons des partenaires de terrain',
      body: 'Se connecter aux organisations qui accèdent directement aux signaux de terrain est la prochaine étape la plus importante pour AEGIRON.',
      label: 'Nous contacter',
      href: 'contact',
    },
  },

  briefings: {
    metaTitle: 'Bulletins quotidiens',
    metaDescription:
      'Bulletins de situation sur les maladies infectieuses générés automatiquement chaque jour par AEGIRON. Les jours calmes, le bulletin dit que la journée était calme.',
    eyebrow: 'BRIEFINGS',
    title: 'Bulletins quotidiens',
    lead: 'Générés automatiquement chaque jour. Personne ne les retouche : une journée sans fait notable est donc consignée comme telle.',
    blocks: [
      {
        title: 'Comment ils sont produits',
        body: 'Les signaux collectés dans la journée et le niveau de risque de chaque pays sont assemblés en une synthèse. Le format varie d’un jour à l’autre (flash, analyse, terrain, données, entretien). Chaque chiffre d’un bulletin est une valeur que le système a réellement reçue ce jour-là.',
        note: 'Un bulletin est une synthèse, non une prévision. Lorsqu’un jugement sur un pays précis est nécessaire, vérifiez directement les éléments sur le tableau de bord.',
      },
    ],
    cta: {
      title: 'Ce que le système observe aujourd’hui',
      body: 'Le tableau de bord montre tels quels les signaux qui fondent chaque bulletin.',
      label: 'Ouvrir le tableau de bord',
      href: '/dashboard',
    },
  },

  about: {
    metaTitle: 'À propos — AEGIRON',
    metaDescription:
      'AEGIRON construit un système d’alerte précoce qui saisit les signaux des maladies infectieuses avant qu’ils ne deviennent une actualité internationale. Busan, Corée du Sud. Nous énonçons clairement notre stade actuel et notre direction.',
    eyebrow: 'ABOUT',
    title: 'AEGIRON',
    lead:
      'Le 31 décembre 2019, les autorités sanitaires de Wuhan, en Chine, signalaient des cas de pneumonie de cause inconnue. L’Organisation mondiale de la santé a déclaré une urgence de santé publique de portée internationale un mois plus tard. Les signaux ne manquaient pas pendant ce mois. Ils existaient — dans les langues locales, là où la veille internationale regarde rarement.\n\nAEGIRON est né pour réduire cet écart. Il recueille, dans leur langue d’origine, les traces qui bougent avant les annonces officielles — presse en langue locale, volumes de recherche, eaux usées, commerce, signaux de maladies animales — et calcule chaque heure où, dans le monde, quelque chose s’écarte de la normale. Chacune de nos prévisions est scellée au moment même où elle est produite, puis publiée, afin que chacun puisse vérifier si elle était juste ou non.',
    photo: {
      src: '/media/photos/earth-at-night.jpg',
      alt: 'La Terre de nuit — lumières urbaines des Amériques (composite satellitaire)',
      caption: 'La Terre de nuit (Black Marble). Un composite d’observations satellitaires.',
      credit: 'NASA Earth Observatory · Domaine public',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:Black_Marble_Americas.jpg',
      position: 'center 40%',
    },
    blocks: [
      {
        title: 'Ce que nous construisons',
        kicker: 'WHAT WE BUILD',
        tone: 'teal',
        body: 'Nous réunissons la presse en langue locale de 178 pays, les données officielles de surveillance et les signaux environnementaux, commerciaux et génomiques en un seul indice, jugeons l’anomalie de chaque pays au regard de sa propre ligne de base et — dès qu’une alerte est émise — calculons à côté les scénarios de propagation et les effets d’intervention. L’axe de conception est de ne pas s’arrêter à la détection mais de répondre à « et alors, et à quelle intensité ».',
        points: [
          'Détecter → juger → prévoir → simuler → prescrire → auto-vérifier → sceller. Toute la chaîne tient dans un seul système.',
          'Chaque prévision est évaluée automatiquement au regard des déclarations officielles qui suivent, et scellée au moment où elle est faite pour ne pouvoir être modifiée après coup.',
          'Deux programmes de R&D internes — criblage génomique défensif (HEIMDALL) et préparation en contre-mesures (VALHALLA) — portent l’axe de biosécurité nationale.',
        ],
      },
      {
        title: 'Où nous en sommes',
        kicker: 'WHERE WE ARE',
        tone: 'indigo',
        body: 'Le système tourne réellement. Les signaux arrivent des sources de données chaque heure, et le tableau de bord en direct est ouvert en ce moment, sans authentification. Nous cherchons un premier partenaire, et nous le disons clairement — l’ouverture et la vérifiabilité sont les forces de ce stade.',
        points: [
          '118 modules et 128 points d’accès tournent chaque heure, et seul le code qui passe 2 263 tests automatisés est mis en production.',
          'Le système, la méthodologie, les données et les limites sont tous ouverts dès le départ, dans un état que la diligence peut vérifier directement.',
          'Chaque prévision est scellée et s’accumule, de sorte qu’un historique vérifiable grandit de lui-même à mesure que l’exploitation continue.',
        ],
      },
      {
        title: 'Pourquoi nous publions tout',
        body: 'Si, sans client ni contrat, on construit des choses à cacher, elles deviennent toutes des passifs au moment d’être validé. Tout ouvrir maintenant, c’est rester prêt à être vérifié. C’est aussi un choix qu’un concurrent de grande taille ne peut structurellement copier — il a des contrats clients à protéger ; nous pouvons ouvrir parce que nous n’en avons aucun. La faiblesse et la force viennent du même endroit.',
        note: 'Notre état de validation et nos limites connues sont exposés intégralement sur une page dédiée.',
      },
      {
        title: 'Où nous allons',
        kicker: 'ROADMAP',
        tone: 'violet',
        items: [
          { title: 'Court terme', body: 'Nous connecter à des organisations de terrain et des réseaux de surveillance réels pour nous rapprocher de la source du signal. Réassureurs, gouvernements, organismes internationaux et organisations de terrain sont les premiers partenaires candidats.' },
          { title: 'Moyen terme', body: 'Poursuivre l’exploitation pour accumuler un historique de prévisions vérifiable. Le registre scellé est le fondement du « nous l’avions bien prévu, alors ».' },
          { title: 'Long terme', body: 'Devenir une infrastructure mondiale d’alerte précoce réellement utilisée dans les régions où la surveillance est mince.' },
        ],
      },
    ],
    cta: {
      title: 'Nous cherchons des personnes avec qui échanger',
      body: 'Réassurance, gouvernement, organismes internationaux, organisations de terrain — tous bienvenus. Vous pouvez d’abord voir le système entier, sans réserver de démonstration.',
      label: 'Nous contacter',
      href: 'contact',
    },
  },

  contact: {
    metaTitle: 'Contact',
    metaDescription: 'Comment joindre AEGIRON.',
    eyebrow: 'CONTACT',
    title: 'Contact',
    lead: 'Vous pouvez examiner l’ensemble du système sans réserver de démonstration. Si, après cet examen, vous avez des questions ou une proposition de collaboration, écrivez-nous ci-dessous.',
    blocks: [
      {
        title: 'Coordonnées',
        items: [
          { title: 'Courriel', body: 'kimdaeheuk@gmail.com', meta: 'La voie la plus rapide' },
          { title: 'Localisation', body: 'Busan, Corée du Sud', meta: 'KST (UTC+9)' },
        ],
      },
      {
        title: 'Particulièrement bienvenus',
        points: [
          '**Corrections** — signalez-nous les erreurs de méthodologie ou de chiffres ; nous les vérifierons et en tiendrons compte.',
          '**Mise en relation avec des organisations de terrain** — un accès aux réseaux de surveillance réels est notre prochaine étape la plus importante.',
          '**Discussions de pilote** — réassureurs, gouvernements, organismes internationaux et organisations de terrain sont tous les bienvenus.',
        ],
      },
    ],
  },

  privacy: {
    metaTitle: 'Politique de confidentialité',
    metaDescription: 'Politique de confidentialité du site AEGIRON.',
    eyebrow: 'LEGAL',
    title: 'Politique de confidentialité',
    lead: 'Ce site n’exige aucune connexion de ses visiteurs et ne collecte aucune donnée personnelle.',
    blocks: [
      {
        title: 'Ce que nous ne collectons pas',
        points: [
          'Il n’y a ni inscription ni connexion : aucune information de compte n’est collectée.',
          'Ce site n’utilise aucun outil de suivi publicitaire ni de mesure d’audience.',
          'La consultation du tableau de bord ne requiert aucune information d’identification personnelle.',
        ],
      },
      {
        title: 'Services externes',
        body: 'La vidéo de présentation de la page d’accueil est intégrée en mode de confidentialité renforcée de YouTube ; les règles de YouTube s’appliquent dès sa lecture. Les polices sont chargées depuis Google Fonts et jsDelivr, qui peuvent enregistrer des données d’accès telles que l’adresse IP.',
      },
      {
        title: 'Lorsque vous nous écrivez',
        body: 'Si vous nous écrivez, le contenu et votre adresse ne servent qu’à vous répondre et ne sont jamais communiqués à des tiers.',
      },
      {
        title: 'Modifications',
        body: 'Si cette politique change, cette page sera mise à jour.',
      },
    ],
  },

  terms: {
    metaTitle: 'Conditions d’utilisation',
    metaDescription: 'Conditions d’utilisation du site AEGIRON et de ses données publiques.',
    eyebrow: 'LEGAL',
    title: 'Conditions d’utilisation',
    lead: 'Les conditions qui s’appliquent lorsque vous utilisez ce site et le tableau de bord public.',
    blocks: [
      {
        title: 'Nature des informations fournies',
        accent: true,
        points: [
          'Les informations de ce site sont fournies **à titre indicatif** et ne constituent pas un fondement de décision médicale, sanitaire ou d’investissement.',
          'Les chiffres de prévision et de scénario sont des **estimations sous hypothèses de modèle** — ni des mesures, ni des garanties.',
          'AEGIRON ne dispose pas encore d’un historique validé de précision en détection précoce.',
          'AEGIRON décline toute responsabilité quant aux conséquences de décisions fondées sur ces informations.',
        ],
      },
      {
        title: 'Sources des données',
        body: 'Ce système collecte et traite des documents publics d’organismes tels que l’OMS et les CDC. Les droits d’auteur et conditions d’utilisation des documents d’origine restent ceux de chaque organisme. Les chiffres traités pouvant différer des originaux, consultez toujours les documents de l’organisme d’origine lorsqu’une citation officielle est nécessaire.',
      },
      {
        title: 'Disponibilité',
        body: 'Le tableau de bord public peut être interrompu ou modifié sans préavis.',
      },
    ],
  },
};
