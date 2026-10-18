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

  techSpec1: {
    metaTitle: 'Technologie I — la couche de veille permanente',
    metaDescription:
      'Les moteurs qui tournent automatiquement chaque heure : veille de la presse en langue locale, indice d’anomalie à six couches, veille des silences de déclaration, foyers inexpliqués, détection d’aberration CDC EARS et veille des défaillances silencieuses. La méthode et les limites de chaque moteur, énoncées clairement.',
    eyebrow: 'TECHNOLOGY · I',
    title: 'La couche de veille permanente',
    lead: 'Parmi les 114 modules algorithmiques d’AEGIRON, voici ceux qui tournent d’eux-mêmes chaque heure, sans qu’on le demande. Leur rôle : compter sans cesse ce qui s’écarte de la normale. Pour chaque moteur, nous indiquons ce qu’il prend comme référence et ce qu’il refuse délibérément de compter.',
    photo: {
      src: '/media/photos/iss-city-lights.jpg',
      alt: 'Lumières urbaines de nuit vues depuis la Station spatiale internationale',
      caption: 'La Türkiye de nuit, vue depuis la Station spatiale internationale. Les réseaux qui font circuler personnes et marchandises sont aussi les voies d’une épidémie.',
      credit: 'NASA JSC · Domaine public',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:The_city_lights_of_T%C3%BCrkiye_sparkle_below_the_International_Space_Station_(iss074e0225549).jpg',
    },
    blocks: [
      {
        title: 'Veille de la presse en langue locale',
        body: 'Avant que la presse internationale ne le traduise, le premier signal est souvent un article en langue locale. Nous prenons 179 pays dans l’actualité agrégée par pays et par langue, mesurons la densité du vocabulaire épidémiologique et reclassons les flux ambigus avec un modèle de langage. Nous n’écartons pas les pays à faible risque par curation — une pandémie peut commencer n’importe où, et les pays calmes sont laissés dormants par les seuils en aval, pas par nous.',
        points: [
          'L’unité de détection est le croisement pays × langue × maladie — un pays vu dans une seule fenêtre d’agrégation, non dispersé entre médias.',
          'La décision finale de haute alerte est menée par le classifieur à modèle de langage, les mots-clés servant de repli — les mots-clés seuls laissent passer des articles sans rapport.',
          'Quand plusieurs flux rapportent le même événement, nous les regroupons comme redondants et les excluons de l’alerte.',
        ],
        note: 'Les flux à données trop rares sont mis à part comme « indéterminés », non élevés en alertes. Nous ne passons pas en silence sur le fait que les données sont minces.',
      },
      {
        title: 'Indice d’anomalie à six couches',
        body: 'Les signaux de six couches — officielle, officieuse, comportementale, environnementale, animale et inexpliquée — sont convertis en scores d’anomalie par rapport à leur niveau habituel, pondérés par la fiabilité de la source, puis combinés en un seul indice. La référence est la ligne de base de chaque indicateur, non son volume absolu : un même décompte n’a pas le même sens dans un pays qui déclare beaucoup et dans un pays habituellement silencieux.',
        points: [
          'Chaque signal est scoré comme un écart (z-score) à sa propre distribution historique, la dernière valeur étant exclue de la ligne de base.',
          'Chaque couche porte une pondération de fiabilité différente — une API gouvernementale officielle et un décompte de publications sociales ne peuvent peser pareil.',
          'Les signaux anciens contribuent de moins en moins avec le temps (décroissance à demi-vie).',
        ],
        note: 'Cet indice ne regarde que les hausses. La baisse — un canal qui se tait — est traitée par la veille des silences ci-dessous.',
      },
      {
        title: 'Veille des silences de déclaration',
        body: 'Les signaux qui montent ne sont pas les seuls dangereux. Quand un canal de déclaration habituellement actif se tait soudain, c’est en soi un signal — le système de déclaration a pu s’effondrer. Lors d’Ebola en Guinée en 2014, les déclarations du ministère ont chuté d’abord ; des semaines après que l’OMS l’eut lu comme « calme », l’épidémie a explosé.',
        points: [
          'Un canal est retenu quand la valeur du jour tombe sous la moitié de sa moyenne historique.',
          'Seuls les indicateurs dotés d’une règle de décision explicitement déclarée sont surveillés — une conception par liste d’autorisation, pour qu’un « 0 » issu d’un rapport non encore déposé ne soit pas pris pour un effondrement.',
        ],
        note: 'Cette conception résulte d’une refonte après que la couche eut émis quatre fausses alertes lors du rodage d’avant-lancement en 2026-09. Nous avons gardé l’échec au dossier et l’avons corrigé.',
      },
      {
        title: 'Foyers inexpliqués',
        body: 'Parmi les foyers extraits de la presse, nous comptons à part ceux qui ne correspondent à aucun profil de maladie connu. Le foyer de pneumonie d’origine inconnue de Wuhan, en décembre 2019, en est l’archétype — l’objectif est de saisir « ceci ne ressemble pas au reste » avant que cela n’ait un nom.',
        points: [
          'Au moment de l’extraction, nous demandons directement au modèle de langage si le cas correspond à un profil de maladie connu. Nous ne forçons pas un cas dans la catégorie « inexpliqué » au seul motif qu’il manque à un petit dictionnaire d’alias.',
          'Quand le même événement revient avec seulement sa formulation changée, nous le regroupons au niveau du pays pour que la même alerte ne se déclenche pas chaque jour.',
        ],
        note: 'Des trois conditions proposées par le document de transmission, une flambée des visites hospitalières ne peut être mesurée — il n’en existe pas de source. Nous la laissons vide plutôt que de la combler par une fabrication.',
      },
      {
        title: 'Détection d’aberration standard · veille des défaillances silencieuses',
        body: 'Nous ajoutons le standard de la surveillance épidémiologique (les CDC américains, EARS C1/C2/C3), qui fonctionne même avec une ligne de base courte. Au-dessus se tient une couche de plus — compter, à chaque cycle, si une source a réellement renvoyé une valeur et si la méthode qui l’a produite tient toujours.',
        items: [
          { title: 'CDC EARS', body: 'Trois fenêtres (C1, C2, C3) demandent de combien de σ la valeur du jour dépasse la ligne de base récente. Une bande de garde empêche les valeurs de début d’épidémie de contaminer la ligne de base.', meta: 'Un standard opérationnel des CDC américains' },
          { title: 'Santé des sources', body: 'Une source dont la collecte a tourné sans rien renvoyer n’est pas comptée comme saine. Les sources qui ne réussissent qu’occasionnellement sont signalées à part.', meta: 'Une source morte en silence est la défaillance la plus dangereuse' },
          { title: 'Invariants de qualité', body: 'Compte les cas où la source est saine mais le calcul qui a produit sa valeur est cassé. Les six incidents de 2026-08 étaient tous de ce type.', meta: 'Une couche que la santé des sources ne peut structurellement voir' },
        ],
      },
    ],
    cta: {
      title: 'Les moteurs plus profonds sont dans Technologie II',
      body: 'Criblage génomique, simulation de propagation entre pays, scénarios d’intervention par alerte, évaluation automatique des prévisions — la couche qui tourne à la demande ou sur alerte.',
      label: 'Voir Technologie II',
      href: 'technology-advanced',
    },
  },

  techSpec2: {
    metaTitle: 'Technologie II — génomique, simulation, réponse, auto-vérification',
    metaDescription:
      'Les moteurs profonds qui tournent à la demande ou sur alerte : naturel de l’ordre des séquences mesuré, détection de chimères par homologie, simulation de propagation entre pays, estimation de la date d’importation, scénarios d’intervention par alerte, évaluation automatique des prévisions et scellement des prévisions — chacun avec sa base mesurée et ses limites.',
    eyebrow: 'TECHNOLOGY · II',
    title: 'Génomique · simulation · réponse · auto-vérification',
    lead: 'Si la couche permanente compte ce qui diffère, cette couche répond à quoi faire, et comment. L’essentiel se calcule à la demande ou sur alerte — c’est lourd, et rien ne justifie de le faire chaque heure. Chaque nombre porte, à côté de lui, jusqu’où on peut lui faire confiance.',
    photo: {
      src: '/media/photos/avian-influenza-h5n1.jpg',
      alt: 'Micrographie électronique en transmission colorisée de particules du virus de la grippe aviaire A(H5N1)',
      caption: 'Particules du virus de la grippe aviaire A(H5N1), micrographie électronique en transmission colorisée. Document public des CDC américains.',
      credit: 'CDC / Cynthia Goldsmith · Domaine public',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:Colorized_transmission_electron_micrograph_of_Avian_influenza_A_H5N1_viruses.jpg',
    },
    blocks: [
      {
        title: 'Génomique — naturel de l’ordre',
        body: 'Les statistiques de composition (GC, CpG, usage des codons) ne regardent que la composition des bases. Elles manquent une séquence dont la composition est naturelle mais dont l’ordre ne l’est pas — assemblée ou recombinée. Nous donnons à un modèle génomique de fondation seulement le début d’une séquence, lui faisons prédire les bases suivantes, et mesurons le naturel de l’ordre directement par la concordance avec la séquence réelle.',
        points: [
          'Mesuré (2026-07) : les séquences naturelles concordent étroitement, et mélanger l’ordre à composition identique fait chuter la concordance — cela saisit l’angle que les statistiques de composition ne peuvent voir.',
          'Il produit une « priorité d’examen complémentaire », non un verdict. Une faible concordance ne signifie pas à elle seule une séquence conçue.',
        ],
        note: 'Ce modèle a exclu de son entraînement les virus à hôte eucaryote ; il n’est donc pas appliqué aux séquences de coronavirus, de grippe ou d’Ebola — le domaine applicable est déclaré, et hors de celui-ci le score est rapporté sans qu’aucun signalement ne soit levé.',
      },
      {
        title: 'Génomique — détection de chimères par homologie',
        body: 'Pour éviter l’angle mort d’un modèle entraîné (les taxons laissés hors de l’entraînement), nous recherchons une séquence protéique dans des bases d’homologie publiques pour voir si une protéine naturelle couvre toute la longueur de la requête. Pour une protéine naturelle, des proches couvrent toute l’étendue ; pour une séquence assemblée à partir de fragments de plusieurs organismes, aucune protéine naturelle ne la couvre entièrement — la trace directe d’une recombinaison.',
        points: [
          'Comme il s’agit d’une recherche en base et non d’un modèle, elle fonctionne aussi sur les virus.',
          'Les seuils ont été pré-enregistrés pour qu’un test de faux positifs — incluant délibérément des pathogènes peu étudiés — soit passé.',
        ],
        note: 'Une faible couverture est une priorité d’examen « non entièrement expliqué par des homologues naturels », non un verdict d’artificialité. Le jugement final requiert un expert, de la phylogénie et un travail de paillasse.',
      },
      {
        title: 'Simulation — propagation entre pays',
        body: 'Un modèle SEIR métapopulationnel avec 159 pays comme nœuds, et 1 671 paires de pays reliées par avion et 314 frontières terrestres comme arêtes. Il rapporte les pays non atteints pendant la période séparément des pays pour lesquels aucune voie n’est connue — « sûr » et « inconnu » ne sont pas le même mot.',
        items: [
          { title: 'Estimation de la date d’importation', body: 'À partir du trafic international de la ville d’origine, de la durée de vol et de la croissance exponentielle initiale, il estime les jours jusqu’à un premier cas importé et le risque par point d’entrée.', meta: 'Une estimation de modèle, non une date d’importation observée' },
          { title: 'Limites du réseau', body: 'Le réseau aérien repose sur des données de liaisons de 2014. La connexion entre deux pays change peu, mais les fréquences ont beaucoup changé, et le trafic terrestre est une estimation fondée sur la population.', meta: 'Exposé avec le résultat sous air_network_coverage' },
        ],
      },
      {
        title: 'Réponse — scénarios d’intervention par alerte',
        body: 'Jusqu’ici une alerte s’arrêtait à « ce qui arrive ». Le destinataire n’obtenait aucune réponse à « que faire ». Pour chaque nouvelle alerte critique ou élevée, nous exécutons une simulation SEIR de défense avec des paramètres propres à la maladie et joignons l’écart entre absence de réponse et intervention, en décès et en jours de saturation hospitalière — l’étape qui transforme un outil de prévision en outil de décision.',
        points: [
          'Les coefficients de transmission et les taux de létalité sont des valeurs représentatives de la littérature. Avant calibration au pathogène et à la région réels, ils sont une référence directionnelle — nous disons « N sous hypothèses de modèle », jamais « sauve N ».',
          'Pour une alerte où la maladie ne peut être identifiée, nous ne produisons aucun nombre. Un bilan inventé à partir de constantes génériques serait un nombre sans fondement.',
        ],
      },
      {
        title: 'Auto-vérification — évaluation et scellement',
        body: 'La prétention de « savoir avant les autres » n’est qu’un argument commercial s’il n’existe aucun moyen de la prouver. Nous avons donc mis la vérification dans le code. Les prévisions enregistrées sont évaluées chaque jour au regard des déclarations officielles qui suivent, et chaque prévision est scellée au moment où elle est faite.',
        items: [
          { title: 'Évaluation automatique des prévisions', body: 'Les prévisions non résolues sont confrontées chaque jour aux déclarations officielles et classées en succès, échec ou indéterminé. Les pics de consultation et les mises à jour du nombre de cas ne servent pas de vérité terrain — ce serait évaluer nos signaux avec nos propres signaux.', meta: 'Si l’antériorité mesurée est 0, nous disons 0' },
          { title: 'Registre d’antériorité', body: 'Il fixe le moment où un signal a été vu pour la première fois, avant toute déclaration officielle. Une antériorité reconstituée après coup n’est pas acceptée comme mesure.', meta: 'Il sépare le chargement a posteriori du temps réel' },
          { title: 'Scellement des prévisions', body: 'L’empreinte d’une prévision est ancrée dans un horodatage public (la chaîne Bitcoin). Un tiers peut vérifier lui-même que la prévision n’a pas été réécrite ensuite.', meta: 'Une preuve qu’on ne peut appliquer rétroactivement' },
        ],
      },
    ],
    cta: {
      title: 'Ces deux couches forment une seule chaîne',
      body: 'Détecter → juger → prévoir → simuler → prescrire → auto-vérifier → sceller. L’écran où cette chaîne tourne réellement est le tableau de bord en direct.',
      label: 'Tableau de bord en direct',
      href: '/dashboard',
    },
  },

  programs: {
    metaTitle: 'Programmes spéciaux — HEIMDALL · VALHALLA',
    metaDescription:
      'Les deux programmes de R&D internes d’AEGIRON. HEIMDALL traite le criblage génomique défensif ; VALHALLA, la préparation en contre-mesures. Tous deux opèrent dans une limite d’honnêteté énoncée, sans surévaluer leurs capacités.',
    eyebrow: 'SPECIAL PROGRAMS',
    title: 'HEIMDALL · VALHALLA',
    lead: 'La plupart des couches de veille opèrent à découvert. Mais deux axes sont d’une nature différente — le criblage génomique des menaces biologiques et la préparation nationale en contre-mesures. Parce qu’ils sont sensibles, nous en gérons la responsabilité et l’accès à part ; cette page énonce seulement ce qu’ils font et ne font pas, sans rien surévaluer.',
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
        body: 'Nommé d’après le gardien qui veille sur le pont dans la mythologie nordique. C’est la fonction défensive du criblage de biosécurité — détecter et signaler si une séquence génomique donnée présente des signaux s’écartant des statistiques de l’évolution naturelle. Il examine ensemble les statistiques de composition, le naturel de l’ordre et la couverture d’homologie (la couche génomique de Technologie II).',
        points: [
          '**Détection défensive uniquement.** Il ne conçoit, ne synthétise ni n’optimise de séquences, et ne fournit aucun moyen de contourner le criblage.',
          'Le résultat est une « priorité d’examen approfondi », non un verdict. Un jugement final requiert un expert et un travail de paillasse (is_screening_only).',
          'Bactéries, archées, génomes eucaryotes et phages sont dans le domaine applicable. Les virus à hôte eucaryote en sortent par une limite de modèle, et ce fait est indiqué dans la réponse.',
        ],
        note: 'Le point d’accès exige une authentification et chaque accès est consigné dans un journal d’audit. Relever le niveau de sécurité ne relève pas les affirmations — classifié signifie contrôle d’accès, non traiter le non validé comme validé.',
      },
      {
        title: 'VALHALLA — préparation en contre-mesures',
        body: 'Plutôt que d’imiter une prédiction de neutralisation au niveau moléculaire, il répond aux questions que l’on peut réellement défendre — quelles menaces notre stock ne peut couvrir (l’écart de couverture) et, parmi celles qu’il couvre, lesquelles ne peuvent être produites sur le territoire (l’écart de souveraineté de production). Ce sont les questions centrales de la planification nationale de biosécurité, et tout est calculé à partir de données publiques.',
        items: [
          { title: 'Écart de couverture', body: 'Quelles maladies disposent d’un stock d’urgence international ou d’un produit approuvé par la réglementation. Nous ne touchons pas aux informations non publiques comme les quantités des stocks nationaux.', meta: 'Sources publiques : OMS ICG, openFDA, etc.' },
          { title: 'Souveraineté de production', body: 'À partir de la liste de préqualification de l’OMS, combien de lieux dans le monde peuvent fabriquer un produit donné. Sur 56 produits, 17 n’ont qu’un seul fabricant — un goulot d’étranglement que cela met au jour.', meta: 'Un point unique d’approvisionnement = le risque qu’un stock ne puisse être reconstitué' },
          { title: 'Stade de développement', body: 'Via ClinicalTrials.gov, il décompose « encore en développement » jusqu’à la phase d’essai, séparant les états regroupés sous « pas de stock » (phase 3 en cours vs aucune phase indiquée).', meta: 'La distinction qui fixe la priorité de préparation' },
        ],
      },
      {
        title: 'La limite d’honnêteté',
        accent: true,
        body: 'Les deux programmes prennent pour règle de fonctionnement de ne pas surévaluer leurs capacités. La limite est fixée dans les commentaires du code, et la réponse la transporte avec elle.',
        points: [
          'HEIMDALL reste une **priorité de criblage, non un verdict.**',
          'L’efficacité de VALHALLA est un **agrégat de l’efficacité déclarée (étiquette) de chaque contre-mesure**, non une prédiction de neutralisation moléculaire.',
          'Là où les données manquent, il ne les invente pas et laisse prudemment la couverture « inconnue ».',
        ],
        note: 'Les noms de code des programmes et la structure organisationnelle sont des définitions internes propres à AEGIRON, non une affiliation à un organisme gouvernemental ni une classification de sécurité officielle.',
      },
    ],
    cta: {
      title: 'La base mesurée des moteurs profonds',
      body: 'Les mesures par taxon de la couche génomique et les limites de réseau de la simulation sont exposées dans Technologie II.',
      label: 'Voir Technologie II',
      href: 'technology-advanced',
    },
  },


  transparency: {
    metaTitle: 'Validation et limites — ce qui n’est pas encore prouvé et les lacunes connues',
    metaDescription:
      'Tout ce qu’AEGIRON n’a pas encore validé, ses limites connues et ses lacunes de données — ainsi que la façon dont le système vérifie ses propres chiffres.',
    eyebrow: 'VALIDATION & LIMITS',
    title: 'Validation et limites',
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
    metaTitle: 'À propos — AEGIRON',
    metaDescription:
      'AEGIRON construit un système d’alerte précoce qui saisit les signaux des maladies infectieuses avant qu’ils ne deviennent une actualité internationale. Busan, Corée du Sud. Nous énonçons clairement notre stade actuel et notre direction.',
    eyebrow: 'ABOUT',
    title: 'AEGIRON',
    lead: 'Une pandémie n’est jamais déclarée de nulle part. Des semaines avant la déclaration, elle laisse des traces — dans la presse locale, les recherches, les eaux usées, le commerce. AEGIRON rassemble ces traces avant leur traduction et calcule, chaque heure, où quelque chose s’écarte de la normale. Nous sommes établis à Busan, en Corée du Sud.',
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
        body: 'Nous réunissons la presse en langue locale de 179 pays, les données officielles de surveillance et les signaux environnementaux, commerciaux et génomiques en un seul indice, jugeons l’anomalie de chaque pays au regard de sa propre ligne de base et — dès qu’une alerte est émise — calculons à côté les scénarios de propagation et les effets d’intervention. L’axe de conception est de ne pas s’arrêter à la détection mais de répondre à « et alors, et à quelle intensité ».',
        points: [
          'Détecter → juger → prévoir → simuler → prescrire → auto-vérifier → sceller. Toute la chaîne tient dans un seul système.',
          'Chaque prévision est évaluée automatiquement au regard des déclarations officielles qui suivent, et scellée au moment où elle est faite pour ne pouvoir être modifiée après coup.',
          'Deux programmes de R&D internes — criblage génomique défensif (HEIMDALL) et préparation en contre-mesures (VALHALLA) — portent l’axe de biosécurité nationale.',
        ],
      },
      {
        title: 'Où nous en sommes',
        body: 'Nous sommes à un stade précoce. Nous ne l’estomperons pas — la due diligence le fait apparaître de toute façon, et dès qu’on l’estompe, la crédibilité de tout le reste tombe avec.',
        points: [
          'Le système tourne réellement. Les signaux arrivent des sources de données chaque heure, et le tableau de bord en direct est ouvert en ce moment, sans authentification.',
          'Nous n’avons pas encore de clients commerciaux. Nous cherchons un premier partenaire.',
          'Aucun organisme externe ne nous a validés de façon indépendante. À ce jour, les seules personnes à avoir évalué ce système sont celles qui l’ont construit.',
          'Nous ne détenons aucun historique validé de détection précoce. Avec une exploitation continue, il s’accumule de lui-même, sous forme de prévisions scellées.',
        ],
      },
      {
        title: 'Pourquoi nous publions tout',
        body: 'Si, sans client ni contrat, on construit des choses à cacher, elles deviennent toutes des passifs au moment d’être validé. Tout ouvrir maintenant, c’est rester prêt à être vérifié. C’est aussi un choix qu’un concurrent de grande taille ne peut structurellement copier — il a des contrats clients à protéger ; nous pouvons ouvrir parce que nous n’en avons aucun. La faiblesse et la force viennent du même endroit.',
        note: 'Notre état de validation et nos limites connues sont exposés intégralement sur une page dédiée.',
      },
      {
        title: 'Où nous allons',
        items: [
          { title: 'Court terme', body: 'Nous connecter à des organisations de terrain et des réseaux de surveillance réels pour nous rapprocher de la source du signal. Réassureurs, gouvernements, organismes internationaux et organisations de terrain sont les premiers partenaires candidats.' },
          { title: 'Moyen terme', body: 'Poursuivre l’exploitation pour accumuler un historique de prévisions vérifiable. Le registre scellé est le fondement du « nous l’avions bien prévu, alors ».' },
          { title: 'Long terme', body: 'Devenir une infrastructure d’alerte précoce réellement utilisée dans les régions où la surveillance est mince.' },
        ],
      },
    ],
    cta: {
      title: 'Si cela vous semble valoir une conversation',
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
