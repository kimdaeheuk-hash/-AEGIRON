import type { PagesDict } from '../types';

/**
 * Contenu français des pages secondaires.
 *
 * ★ Tous les chiffres sont mesurés au 2026-08-06 ★
 * 21 sources · 106 points d’accès · 81 modules algorithmiques · 740 tests
 * automatisés validés · 217 pays référencés. Aucune estimation n’est présentée
 * comme un fait.
 *
 * ★ RÈGLE ABSOLUE ★ Aucune affirmation de précision ni de délai d’avance.
 */
export const pagesFr: PagesDict = {
  platform: {
    metaTitle: 'Système — du signal à l’alerte',
    metaDescription:
      'Les cinq étapes d’AEGIRON — collecter, extraire, juger, prévoir, agir — et ce que chaque étape écarte délibérément.',
    eyebrow: 'SYSTÈME',
    title: 'Du signal à l’alerte',
    lead: 'La qualité d’un système de veille tient moins à ce qu’il capte qu’à ce qu’il écarte. Voici ce que chacune des cinq étapes retient, et ce qu’elle laisse tomber.',
    blocks: [
      {
        title: '01 · Collecter',
        body: 'Les signaux arrivent automatiquement de 21 sources. Un rapport officiel et un article de presse locale ne sont pas des preuves de même nature : chaque source conserve donc son propre niveau de confiance dans tout le reste du système.',
        items: [
          { title: 'Sources officielles', body: 'Rapports de situation et bulletins d’épidémie de l’OMS, Africa CDC, avis aux voyageurs des CDC. Nous reprenons le niveau de gravité attribué par chaque institution — nous n’en inventons jamais.' },
          { title: 'Presse en langue locale', body: 'Des reportages antérieurs à la couverture internationale, y compris dans des pays trop peu rentables pour que d’autres s’y intéressent.' },
          { title: 'Indicateurs environnementaux et indirects', body: 'Climat, changement forestier satellitaire, statistiques d’importation d’équipements de protection, surveillance des eaux usées. Ils approchent les conditions d’une épidémie et les préparatifs, pas l’épidémie elle-même.' },
        ],
        note: 'Les statistiques commerciales accusent environ deux mois de retard de déclaration : c’est un indicateur de moyen terme, pas de temps réel. Chaque réponse le précise.',
      },
      {
        title: '02 · Extraire',
        body: 'Maladie, pays, cas et décès sont structurés à partir des tableaux PDF et du texte des articles. Une seule règle gouverne cette étape : ce qui n’est pas reconnu est laissé vide plutôt que deviné.',
        points: [
          'Les colonnes dont l’en-tête n’est pas compris sont **écartées.** Les remplir par position fausse les chiffres silencieusement.',
          '« Nouveaux sur 7 jours » et « cumulés » restent séparés. Les confondre a déjà transformé 296 nouveaux décès en un cumul de 1 437.',
          '« Probable / suspecté » et « confirmé » sont deux axes distincts. Les additionner transforme des cas suspects en total confirmé.',
          'Les lignes « Total » sont exclues : ce ne sont pas des pays. Sinon un pays nommé `Total` apparaît et contamine toutes les tendances.',
        ],
        note: 'Ces valeurs sont extraites par machine et des erreurs de lecture restent possibles. Les chiffres extraits sont recoupés avec le texte source, et tout ce qui n’y est pas confirmé est signalé.',
      },
      {
        title: '03 · Juger',
        body: 'L’anomalie est mesurée **par rapport au niveau habituel de chaque pays**, et non à un seuil absolu. Cinq signaux ne signifient pas la même chose dans un pays qui déclare en permanence et dans un pays silencieux.',
        points: [
          'L’écart est calculé sur l’historique propre du pays.',
          'Les signaux anciens pèsent de moins en moins (décroissance par demi-vie).',
          '« Mesuré, rien d’anormal » est rapporté séparément de « données insuffisantes pour juger » — les confondre fait lire une semaine ordinaire comme une alerte.',
        ],
      },
      {
        title: '04 · Prévoir',
        body: 'Des modèles de transmission estiment l’ampleur et le risque d’importation. Chaque valeur porte ses hypothèses et ses limites.',
        points: [
          'Les modèles sont calibrés avec les R0 et létalités mesurés dans la littérature, maladie par maladie.',
          'Pour les agents qui n’ont jamais produit d’épidémie générale, la **population atteignable** est plafonnée. Un R0 supérieur à 1 ne signifie pas que toute une population sera infectée.',
          'Les estimations de décès sont automatiquement comparées à la plus grande épidémie enregistrée ; au-delà d’une plage défendable, **l’avertissement accompagne le chiffre**.',
        ],
        note: 'Les chiffres de scénario sont des estimations sous hypothèses de modèle — ni des mesures, ni des garanties.',
      },
      {
        title: '05 · Agir',
        body: 'La sortie ne s’arrête pas à « quelque chose arrive ». Les scénarios sans intervention et avec intervention sont comparés, afin d’indiquer quelles mesures maîtrisent réellement la transmission.',
        items: [
          { title: 'Référence sans intervention', body: 'La trajectoire sans aucune mesure sert de ligne de base.' },
          { title: 'Comparaison des interventions', body: 'Isolement, distanciation, vaccination et traitement sont combinés pour trouver où le taux de reproduction effectif passe sous 1.' },
          { title: 'Horodatage', body: 'Prévisions et scénarios sont scellés par empreinte à leur création. Cela prouve seulement que nous détenions ce contenu à cette date — jamais qu’il était exact.' },
        ],
      },
    ],
    cta: {
      title: 'Le système s’explique mieux que nous',
      body: 'Vous pouvez ouvrir dès maintenant la version en fonctionnement de ces cinq étapes.',
      label: 'Ouvrir le tableau de bord',
      href: '/dashboard',
    },
  },

  transparency: {
    metaTitle: 'Ce que nous ignorons — points non validés et limites connues',
    metaDescription:
      'Tout ce qu’AEGIRON n’a pas encore validé, ses limites connues et ses lacunes de données — ainsi que la façon dont le système vérifie ses propres chiffres.',
    eyebrow: 'CE QUE NOUS IGNORONS',
    title: 'Ce que nous ignorons',
    lead: 'En veille épidémiologique, l’échec le plus dangereux n’est pas une prévision fausse mais une prévision invérifiable. Nous commençons donc par ce dont nous ne sommes pas sûrs. Si nous ne le disons pas, la due diligence le dira à notre place.',
    blocks: [
      {
        title: 'Non validé à ce jour',
        accent: true,
        points: [
          '**Nous n’avons aucun historique validé** de précision en détection précoce. C’est pourquoi aucune affirmation du type « détecté N jours plus tôt » ne figure sur ce site.',
          'Le système est pleinement opérationnel depuis 2026. Les résultats sur des épidémies antérieures sont des **reconstitutions rétrospectives** et n’équivalent pas à une performance réelle.',
          'Les chiffres issus des modules de prévision sont des **estimations sous hypothèses de modèle** — ni des mesures, ni des garanties.',
          'Aucun organisme externe n’a évalué ce système de façon indépendante. À ce jour, seuls ses concepteurs l’ont évalué.',
        ],
        note: 'Ces énoncés évolueront. Quand ce sera le cas, cette page évoluera avec eux.',
      },
      {
        title: 'Limites connues',
        items: [
          {
            title: 'Lacunes de collecte',
            body: 'Des signaux manquent pour certains pays et certaines périodes. Aucun modèle ne peut prévoir une épidémie sur une fenêtre où rien n’a été collecté.',
            meta: 'Le système signale lui-même les fenêtres vides',
          },
          {
            title: 'Taux de fausses alertes',
            body: 'Au niveau de performance actuel, une part importante des alertes ne débouche pas sur une épidémie réelle. La lassitude face aux alertes est le véritable mode d’échec de ces systèmes.',
            meta: 'Le seuil relève de la politique d’exploitation, pas d’une bonne réponse',
          },
          {
            title: 'Erreurs d’extraction automatique',
            body: 'La lecture de chiffres dans des tableaux PDF peut échouer. Le recoupement avec le texte source aide sans être complet.',
            meta: 'Les valeurs non vérifiées sont signalées',
          },
          {
            title: 'Qualité de traduction',
            body: 'Nous avons testé la traduction automatique pour la presse en langue locale et l’avons écartée. En swahili et en amharique, des noms de maladies disparaissaient et des sens s’inversaient.',
            meta: 'La correspondance par mots-clés reste en place faute de mieux',
          },
        ],
      },
      {
        title: 'Ce que le système vérifie donc lui-même',
        body: 'Des limites écrites uniquement dans la documentation finissent séparées des chiffres, et les chiffres finissent dans des présentations sans nuance. Les vérifications vivent donc dans le code.',
        points: [
          '**Comparaison historique** — les estimations de décès sont comparées à la plus grande épidémie enregistrée pour cette maladie ; au-delà d’un facteur dix, la réponse porte un avertissement explicite « ne pas utiliser en externe ».',
          '**Séparation des causes d’échec** — lorsqu’une épidémie est manquée, « le modèle a échoué » est rapporté séparément de « nous n’avions pas de données ». Les confondre inverse le diagnostic.',
          '**Évaluation prospective** — la performance n’est mesurée que sur des périodes invisibles au modèle pendant l’apprentissage, car ajouter des variables améliore presque toujours le score d’apprentissage.',
          '**Traçabilité** — lorsqu’un nom de maladie ou un pays provient du contexte plutôt que du tableau, nous enregistrons son origine.',
        ],
      },
      {
        title: 'Pourquoi cette page existe',
        body: 'Vous ne trouverez pas cette page chez un concurrent : une entreprise avec des clients et des contrats peut difficilement publier ses faiblesses. Nous n’avons encore rien à protéger, donc nous le pouvons — et c’est l’un des rares avantages réels dont nous disposons. C’est aussi la première chose que vérifie la due diligence d’un réassureur : l’équipe connaît-elle ses propres limites.',
      },
    ],
    cta: {
      title: 'Si vous y trouvez une erreur',
      body: 'Si quelque chose ici est inexact ou si une limite manque, dites-le-nous. Les corrections sont appliquées.',
      label: 'Nous contacter',
      href: 'contact',
    },
  },

  dataSources: {
    metaTitle: 'Sources de données — les 21, publiées',
    metaDescription:
      'Les 21 sources de données en temps réel utilisées par AEGIRON, par catégorie, avec leur fréquence de mise à jour et leurs limites.',
    eyebrow: 'SOURCES DE DONNÉES',
    title: '21 sources de données',
    lead: 'Un jugement ne peut pas être vérifié si les éléments qui le fondent sont cachés. Chaque source est listée par nature — avec ce qu’elle ne permet pas de faire.',
    blocks: [
      {
        title: 'Organismes de santé officiels',
        body: 'Les plus fiables et les plus lents, car ils passent par une confirmation formelle. En alerte précoce, ils servent de référence.',
        items: [
          { title: 'Rapports de situation de l’OMS', body: 'Détail hebdomadaire des épidémies en cours. Les tableaux par pays (cas, décès, létalité) sont lus par machine et convertis en signaux.', meta: 'Hebdomadaire' },
          { title: 'Bulletins d’épidémie de l’OMS', body: 'Avis relatifs aux épidémies nouvellement confirmées.', meta: 'Irrégulier' },
          { title: 'Africa CDC', body: 'Situation épidémique dans la région africaine.', meta: 'Hebdomadaire' },
          { title: 'Avis sanitaires aux voyageurs des CDC', body: 'Niveaux d’avis par pays publiés par les CDC américains.', meta: 'Au fil des publications' },
          { title: 'WAHIS (maladies animales)', body: 'Le signal animal des maladies zoonotiques.', meta: 'Au fil des publications' },
          { title: 'KDCA (Corée)', body: 'Statistiques hebdomadaires des maladies à déclaration obligatoire en Corée.', meta: 'Hebdomadaire' },
        ],
      },
      {
        title: 'Presse et médias',
        body: 'Plus rapides que les rapports officiels et bien plus bruyants. Pondérés faiblement et toujours recoupés avec un autre axe.',
        items: [
          { title: 'Presse en langue locale', body: '179 pays. La couverture locale avant que les médias internationaux ne s’en saisissent.', meta: 'Horaire' },
          { title: 'Couverture médiatique GDELT', body: 'Tendances du volume d’actualité mondial — nous observons les poussées d’attention, pas les articles isolés.', meta: 'Quotidien' },
          { title: 'Attention en recherche et réseaux', body: 'Indicateurs d’intérêt du public, comme les consultations encyclopédiques.', meta: 'Quotidien' },
        ],
        note: 'La presse ne bouge qu’après qu’un journaliste a déjà écrit : c’est un indicateur retardé, jamais une source primaire.',
      },
      {
        title: 'Environnement et indicateurs indirects',
        body: 'Ils observent les conditions d’une épidémie et les préparatifs. Ce ne sont pas des preuves directes, mais ils peuvent bouger quand tous les autres axes sont silencieux.',
        items: [
          { title: 'Signaux climatiques', body: 'Conditions de propagation vectorielle (température, précipitations).', meta: 'Quotidien' },
          { title: 'Changement forestier satellitaire', body: 'La destruction d’habitats est liée au risque de passage zoonotique.', meta: 'Hebdomadaire' },
          { title: 'Statistiques commerciales', body: 'Une hausse des importations d’équipements de protection approche les comportements de préparation.', meta: 'Mensuel · ~2 mois de retard' },
          { title: 'Surveillance des eaux usées', body: 'Détection d’agents pathogènes avant l’apparition des symptômes.', meta: 'Hebdomadaire' },
          { title: 'Mobilité aérienne', body: 'Utilisée pour estimer les voies d’importation.', meta: 'Temps réel' },
          { title: 'Signaux de chaîne d’approvisionnement', body: 'Variations de disponibilité (antipyrétiques, masques, etc.).', meta: 'Hebdomadaire' },
        ],
        note: 'La mobilité aérienne est actuellement bloquée depuis nos serveurs cloud et n’est pas reçue. Nous l’indiquons plutôt que de le masquer.',
      },
      {
        title: 'Recherche et génomique',
        items: [
          { title: 'medRxiv · bioRxiv', body: 'Prépublications avant évaluation par les pairs, où un signal peut apparaître avant l’annonce officielle.', meta: 'Quotidien' },
          { title: 'Analyse de séquences génomiques', body: 'Caractérisation des variants et évaluation du caractère naturel des séquences.', meta: 'À la demande' },
          { title: 'InfoDengue (Brésil)', body: 'Comptages hebdomadaires de dengue à l’échelle des villes.', meta: 'Hebdomadaire' },
        ],
      },
    ],
    cta: {
      title: 'Vérifiez si elles fonctionnent en ce moment',
      body: 'Le tableau de bord montre l’état de collecte récent de chaque source.',
      label: 'Ouvrir le tableau de bord',
      href: '/dashboard',
    },
  },

  methodology: {
    metaTitle: 'Méthodologie — quatre couches',
    metaDescription:
      'La méthodologie d’AEGIRON en quatre couches : collecte, extraction, analyse et prévision. Des méthodes académiques établies, assemblées en produit.',
    eyebrow: 'MÉTHODOLOGIE',
    title: 'Quatre couches',
    lead: 'Nous n’avons pas inventé de nouvelles mathématiques. Nous avons pris des méthodes déjà établies en épidémiologie des maladies infectieuses et en épidémiologie de veille, et les avons assemblées en un produit qui tourne seul, chaque jour. Voici la norme suivie par chaque couche.',
    blocks: [
      {
        title: 'Couche 1 · Collecte',
        body: 'Vingt et une sources hétérogènes sont normalisées en un format de signal unique. La confiance varie selon la source : elle est donc stockée avec la valeur et utilisée comme pondération dans tous les calculs ultérieurs.',
      },
      {
        title: 'Couche 2 · Extraction',
        body: 'Des chiffres structurés sont extraits de documents non structurés — tableaux PDF et texte d’articles. Les images de page sont interprétées bloc par bloc, puis les chiffres extraits sont recoupés avec le texte brut. Ce qui n’y est pas confirmé est marqué comme non vérifié.',
      },
      {
        title: 'Couche 3 · Analyse',
        body: 'Cette couche suit les conventions de l’épidémiologie de veille. La détection d’anomalie utilise des scores z par rapport à la référence nationale et des méthodes de la famille CDC EARS ; la performance s’exprime en sensibilité, spécificité, valeur prédictive positive et taux de fausses alertes.',
        points: [
          'Sensibilité (POD) = part des épidémies réelles détectées',
          'Spécificité = part des périodes ordinaires correctement laissées de côté',
          'Taux de fausses alertes (FAR) = part des alertes non fondées',
          'Le bon taux de fausses alertes relève de la **politique d’exploitation, pas de la technique** — combien d’alertes une équipe peut examiner par jour, et combien un manquement coûte de plus qu’une fausse alerte, sont des décisions d’organisation. Nous ne choisissons donc pas de seuil : nous montrons toute la courbe caractéristique.',
        ],
      },
      {
        title: 'Couche 4 · Prévision',
        body: 'Un modèle compartimental SEIR standard avec interventions variables dans le temps estime la trajectoire. Les paramètres par maladie proviennent de valeurs mesurées dans la littérature.',
        points: [
          'Les agents à transmission limitée par contact voient leur **population atteignable** plafonnée. Appliquer le R0 de 1,8 d’Ebola à une population entière produit 87 fois la plus grande épidémie de l’histoire — cela s’est réellement produit, et nous l’avons corrigé.',
          'L’effet d’une intervention se juge au passage du taux de reproduction effectif sous 1.',
          'Chaque résultat est étiqueté « scénario de modèle » et accompagné de sa comparaison historique.',
        ],
      },
      {
        title: 'Où cela se situe',
        body: 'Associer prévision et simulation en modélisation épidémique est un domaine travaillé depuis plus de dix ans par l’Imperial College MRC GIDA, le MOBS Lab de Northeastern et d’autres. Ce qu’AEGIRON a construit n’est pas la méthode mais **la structure qui fait tourner ces méthodes automatiquement, chaque jour, comme un produit commercial.** Nous ne revendiquons aucune première mondiale.',
      },
    ],
  },

  solutionsReinsurance: {
    metaTitle: 'Pour la réassurance et l’assurance',
    metaDescription:
      'Indices d’exposition par pays et comparaison de portefeuille — toujours présentés comme des indices relatifs, jamais comme des probabilités absolues.',
    eyebrow: 'POUR LA RÉASSURANCE',
    title: 'Réassurance et assurance',
    lead: 'La place de la quantification du risque pandémique est aujourd’hui vacante. Ce que nous produisons reste toutefois un indice relatif et non une probabilité — et la réponse rend cette distinction explicite plutôt que de la laisser au lecteur.',
    blocks: [
      {
        title: 'Ce que vous obtenez',
        items: [
          { title: 'Indice d’exposition par pays', body: 'Un indice de 0 à 100 synthétisant pression du signal, vulnérabilité et potentiel de diffusion, conçu pour la comparaison et le classement.' },
          { title: 'Comparaison de portefeuille', body: 'Vos pays en une seule vue, classés en percentile relatif.' },
          { title: 'Contrefactuel d’intervention', body: 'L’écart modélisé entre absence d’action et scénarios d’intervention.' },
          { title: 'Historique scellé', body: 'Les prévisions sont scellées à leur création : un historique vérifiable se constitue de lui-même avec le temps.' },
        ],
      },
      {
        title: 'Ce qu’il faut savoir',
        accent: true,
        points: [
          'L’indice d’exposition **n’est pas une probabilité absolue.** Chaque réponse porte `is_probability: false`.',
          'Les pondérations sont des choix de politique, non des valeurs calibrées empiriquement. `weights_calibrated: false` est indiqué explicitement.',
          'Il n’existe pas encore d’historique de prévision validé. Ce n’est pas au stade d’alimenter directement une tarification.',
        ],
      },
    ],
    cta: {
      title: 'Commencez par la due diligence',
      body: 'Le système entier est ouvert : vérifiez d’abord, nous en parlerons ensuite.',
      label: 'Nous contacter',
      href: 'contact',
    },
  },

  solutionsGovernment: {
    metaTitle: 'Pour les gouvernements et la santé publique',
    metaDescription:
      'Traçage des voies d’importation et comparaison des interventions, avec l’effet modélisé de chaque mesure.',
    eyebrow: 'POUR LES GOUVERNEMENTS',
    title: 'Gouvernements et santé publique',
    lead: 'Deux questions ensemble : comment une épidémie étrangère atteint votre population, et quelles mesures maîtrisent réellement la transmission.',
    blocks: [
      {
        title: 'Ce que vous obtenez',
        items: [
          { title: 'Traçage des voies d’importation', body: 'Voies de risque estimées à partir de la connectivité aérienne et d’une pondération par ville.' },
          { title: 'Comparaison des interventions', body: 'Combinaisons d’isolement, de distanciation, de vaccination et de traitement, à la recherche du minimum qui fait passer le taux de reproduction effectif sous 1.' },
          { title: 'Estimation de la charge hospitalière', body: 'Jours de dépassement des capacités en lits estimés à partir de la courbe épidémique.' },
          { title: 'Bulletin quotidien', body: 'Un résumé de situation généré automatiquement. Les jours calmes, il le dit.' },
        ],
      },
      {
        title: 'Ce qu’il faut savoir',
        accent: true,
        points: [
          'Les chiffres de scénario sont des **estimations sous hypothèses de modèle.** Une revue épidémiologique est nécessaire avant tout usage en appui de décision publique.',
          'Lorsqu’une valeur sort de ce que l’histoire peut expliquer, le système y joint son propre avertissement.',
        ],
      },
    ],
    cta: {
      title: 'Ouvrez-le d’abord',
      body: 'Tout ce qui est nécessaire à une évaluation est déjà public.',
      label: 'Nous contacter',
      href: 'contact',
    },
  },

  solutionsNgo: {
    metaTitle: 'Pour les organisations internationales et humanitaires',
    metaDescription:
      'Signaux précoces dans les zones à surveillance faible — y compris des pays que d’autres délaissent faute de rentabilité.',
    eyebrow: 'ORGANISATIONS INTERNATIONALES ET HUMANITAIRES',
    title: 'Organisations internationales et humanitaires',
    lead: 'Plus la surveillance est faible, plus le signal est tardif. Ces régions étant peu rentables, peu d’acteurs les couvrent — c’est précisément pourquoi nous le faisons.',
    blocks: [
      {
        title: 'Ce que vous obtenez',
        items: [
          { title: 'Priorité aux régions délaissées', body: 'Nigéria, Éthiopie, Yémen, Madagascar, Papouasie-Nouvelle-Guinée et d’autres pays où les lacunes de surveillance sont importantes.' },
          { title: 'Première couverture locale', body: 'La presse locale avant l’implication des médias internationaux.' },
          { title: 'Détection d’événements inexpliqués', body: 'Les foyers qu’aucune maladie connue n’explique sont signalés à part.' },
          { title: 'Signalement des lacunes', body: 'Le système indique quelles régions et périodes sont vides — une information opérationnellement utile en soi.' },
        ],
      },
      {
        title: 'Ce qu’il faut savoir',
        accent: true,
        points: [
          'Plus la surveillance d’une région est faible, **plus nos propres données y sont probablement vides.** Les lacunes sont affichées, pas masquées.',
          'Le traitement en langue locale repose sur des mots-clés et non sur la traduction automatique, celle-ci ayant échoué à notre contrôle qualité.',
        ],
      },
    ],
    cta: {
      title: 'Nous cherchons des partenaires de terrain',
      body: 'Entrer en relation avec des organisations proches des signaux réels est notre étape suivante la plus précieuse.',
      label: 'Nous contacter',
      href: 'contact',
    },
  },

  briefings: {
    metaTitle: 'Bulletins quotidiens',
    metaDescription:
      'Le bulletin épidémiologique quotidien généré automatiquement par AEGIRON. Les jours calmes, il le dit.',
    eyebrow: 'BULLETINS',
    title: 'Bulletins quotidiens',
    lead: 'Générés automatiquement chaque jour. Comme aucun humain ne les retouche, une journée sans événement se lit comme une journée sans événement.',
    blocks: [
      {
        title: 'Comment ils sont produits',
        body: 'Les signaux collectés dans la journée et les scores de risque par pays sont assemblés en un résumé. Le format alterne — édition spéciale, analyse approfondie, reportage de terrain, bulletin de données, entretien. Chaque chiffre d’un bulletin est une valeur réellement reçue ce jour-là.',
        note: 'Un bulletin est un résumé, pas une prévision. Pour un jugement sur un pays précis, vérifiez les éléments sous-jacents sur le tableau de bord.',
      },
    ],
    cta: {
      title: 'Voyez ce que le système observe aujourd’hui',
      body: 'Le tableau de bord montre les signaux à partir desquels un bulletin a été construit.',
      label: 'Ouvrir le tableau de bord',
      href: '/dashboard',
    },
  },

  about: {
    metaTitle: 'À propos',
    metaDescription:
      'AEGIRON développe des systèmes d’alerte précoce des maladies infectieuses depuis Busan, en Corée du Sud. Voici exactement où nous en sommes.',
    eyebrow: 'À PROPOS',
    title: 'AEGIRON',
    lead: 'Nous construisons un système qui capte les signaux de maladies infectieuses avant qu’ils ne deviennent une actualité internationale. Nous sommes basés à Busan, en Corée du Sud.',
    blocks: [
      {
        title: 'Où nous en sommes',
        body: 'Stade précoce. Nous ne l’édulcorerons pas : la due diligence le révélerait de toute façon, et l’édulcorer coûterait la crédibilité de tout le reste.',
        points: [
          'Le système fonctionne réellement. Les signaux arrivent chaque heure de 21 sources et le tableau de bord est ouvert en ce moment.',
          'Nous n’avons pas encore de client commercial. Nous cherchons un premier partenaire.',
          'Aucun organisme externe n’a évalué le système de façon indépendante.',
          'Il n’existe pas d’historique de prévision validé. La poursuite de l’exploitation en constitue un d’elle-même.',
        ],
      },
      {
        title: 'Pourquoi tout publier',
        body: 'Se créer des choses à cacher à un stade sans client ni contrat devient une dette dès que quelqu’un vérifie. Tout ouvrir maintenant nous laisse vérifiables. C’est aussi un choix que des concurrents plus grands peuvent difficilement copier : ils ont des contrats à protéger.',
      },
      {
        title: 'Où cela va',
        items: [
          { title: 'Court terme', body: 'Nous relier à des organisations de terrain et à des réseaux de surveillance pour nous rapprocher de la source des signaux.' },
          { title: 'Moyen terme', body: 'Poursuivre l’exploitation pour accumuler un historique de prévision vérifiable, les enregistrements scellés en faisant foi.' },
          { title: 'Long terme', body: 'Devenir un système réellement utilisé là où les lacunes de surveillance sont les plus grandes.' },
        ],
      },
    ],
    cta: {
      title: 'Si cela vous semble mériter une conversation',
      body: 'Réassurance, gouvernement, organisation internationale ou acteur de terrain — tous bienvenus.',
      label: 'Nous contacter',
      href: 'contact',
    },
  },

  contact: {
    metaTitle: 'Contact',
    metaDescription: 'Comment joindre AEGIRON.',
    eyebrow: 'CONTACT',
    title: 'Contact',
    lead: 'Vous pouvez consulter l’ensemble du système sans réserver de démonstration. Si des questions surgissent ensuite, c’est le bon moment pour écrire.',
    blocks: [
      {
        title: 'Nous joindre',
        items: [
          { title: 'Courriel', body: 'kimdaeheuk@gmail.com', meta: 'La voie la plus rapide' },
          { title: 'Localisation', body: 'Busan, Corée du Sud', meta: 'KST (UTC+9)' },
        ],
      },
      {
        title: 'Particulièrement bienvenu',
        points: [
          '**Corrections** — si la méthodologie ou un chiffre est faux, dites-le-nous. C’est corrigé.',
          '**Mises en relation de terrain** — un accès à de véritables réseaux de surveillance est ce dont nous avons le plus besoin.',
          '**Discussions de pilote** — réassurance, gouvernement ou organisation internationale.',
        ],
      },
    ],
  },

  privacy: {
    metaTitle: 'Politique de confidentialité',
    metaDescription: 'Traitement des données personnelles sur le site AEGIRON.',
    eyebrow: 'MENTIONS LÉGALES',
    title: 'Politique de confidentialité',
    lead: 'Ce site ne demande aucune authentification et ne collecte pas de données personnelles.',
    blocks: [
      {
        title: 'Ce que nous ne collectons pas',
        points: [
          'Il n’y a ni inscription ni connexion : aucune donnée de compte n’est collectée.',
          'Ce site n’utilise pas de traceurs publicitaires.',
          'La consultation du tableau de bord ne requiert aucune information identifiante.',
        ],
      },
      {
        title: 'Si vous nous écrivez',
        body: 'Les courriels que vous envoyez servent uniquement à vous répondre et ne sont pas transmis à des tiers.',
      },
      {
        title: 'Modifications',
        body: 'Si cette politique change, cette page est mise à jour.',
      },
    ],
  },

  terms: {
    metaTitle: 'Conditions d’utilisation',
    metaDescription: 'Conditions d’utilisation du site AEGIRON et de ses données publiques.',
    eyebrow: 'MENTIONS LÉGALES',
    title: 'Conditions d’utilisation',
    lead: 'Ces conditions s’appliquent à ce site et au tableau de bord public.',
    blocks: [
      {
        title: 'Nature des informations fournies',
        accent: true,
        points: [
          'Les informations présentées sont **fournies à titre indicatif** et ne constituent pas une base de décision médicale, sanitaire ou d’investissement.',
          'Les chiffres de prévision et de scénario sont des **estimations sous hypothèses de modèle** — ni des mesures, ni des garanties.',
          'AEGIRON ne dispose pas encore d’un historique validé en matière de précision de détection précoce.',
          'Nous déclinons toute responsabilité quant aux conséquences des décisions prises sur la base de ces informations.',
        ],
      },
      {
        title: 'Provenance des données',
        body: 'Ce système collecte et traite des documents publics de l’OMS, des CDC et d’autres organismes. Les droits et conditions d’utilisation des documents d’origine appartiennent à ces institutions. Les chiffres traités peuvent différer des originaux : pour toute citation formelle, vérifiez auprès de la source d’origine.',
      },
      {
        title: 'Disponibilité',
        body: 'Le tableau de bord public peut être interrompu ou modifié sans préavis.',
      },
    ],
  },
};
