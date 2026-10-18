import type { PagesDict } from '../types';

/**
 * Contenu français des pages secondaires.
 *
 * ★ Les chiffres ici sont des valeurs mesurées ★
 * 23 sources de collecte opérationnelles · 114 modules algorithmiques · 123 points d’accès · 2 145 tests automatisés (mesuré le 2026-10-18).
 * Aucune estimation n’est présentée comme un fait.
 *
 * ★ RÈGLE ABSOLUE ★ Aucune affirmation de précision ni de délai d’avance.
 */
export const pagesFr: PagesDict = {
  platform: {
    metaTitle: 'Système — du signal à l’alerte',
    metaDescription:
      'Les cinq étapes par lesquelles AEGIRON transforme les signaux de maladies infectieuses en alertes — collecter, extraire, juger, prévoir, répondre — et ce que chaque étape écarte délibérément.',
    eyebrow: 'SYSTEM',
    title: 'Du signal à l’alerte',
    lead: 'La qualité d’un système de veille se joue moins sur ce qu’il capte que sur ce qu’il écarte. Pour chacune des cinq étapes, nous indiquons ce que nous retenons et ce que nous rejetons.',
    blocks: [
      {
        title: '01 · Collecter',
        body: 'Les signaux arrivent chaque heure de 23 sources de collecte opérationnelles. Des matériaux de natures très différentes s’y mêlent — des rapports officiels d’organismes internationaux à la presse en langue locale de 179 pays —, si bien que chaque source est conservée avec son propre poids de fiabilité, repris dans tous les calculs ultérieurs.',
        items: [
          { title: 'Déclarations officielles', body: 'Bureaux régionaux de l’OMS pour l’Afrique et les Amériques, Agence coréenne de contrôle et de prévention des maladies, bulletin hebdomadaire japonais des maladies infectieuses, Centre de protection de la santé de Hong Kong et InfoDengue (Brésil). Nous reprenons le niveau de gravité fixé par chaque organisme et n’en inventons jamais.' },
          { title: 'Presse en langue locale', body: 'La couverture locale avant que la presse internationale ne s’empare d’un événement — y compris dans des pays que d’autres services de veille couvrent rarement faute d’intérêt commercial.' },
          { title: 'Signaux environnementaux et indirects', body: 'Surveillance des eaux usées (CDC NWSS, États-Unis), fenêtre de veille post-catastrophe (GDACS), observation polaire et statistiques commerciales de fournitures médicales. Ce sont des indicateurs indirects des conditions d’une épidémie et des comportements de préparation, non des épidémies elles-mêmes.' },
        ],
        note: 'Les statistiques commerciales sont publiées avec un décalage d’environ deux mois et ne constituent pas un indicateur en temps réel. Chaque réponse le précise.',
      },
      {
        title: '02 · Extraire',
        body: 'Maladie, pays, cas et décès sont structurés à partir des tableaux PDF et du texte des articles. Une règle gouverne cette étape : ce qui ne peut être lu reste vide et n’est jamais deviné.',
        points: [
          'Une colonne dont l’en-tête est illisible est **écartée.** La remplir d’après sa position fait dériver les chiffres sans bruit.',
          '« Nouveaux cas sur sept jours » et « cumul » sont tenus séparés. Les confondre ferait passer 296 nouveaux cas pour un cumul de 1 437.',
          '« Probable ou suspect » et « confirmé » relèvent d’axes distincts. Les additionner transforme des cas suspects en total confirmé.',
          'Une ligne « total » n’est pas un pays et est exclue — sinon un pays nommé `Total` apparaît et contamine l’analyse des tendances.',
        ],
        note: 'Les valeurs extraites par machine peuvent être mal lues. Les chiffres extraits sont confrontés au texte source, et ceux qui ne peuvent y être confirmés sont signalés à part.',
      },
      {
        title: '03 · Juger',
        body: 'Les anomalies sont calculées **par rapport au niveau habituel de chaque pays,** non en valeur absolue. Les mêmes cinq cas n’ont pas le même sens dans un pays qui déclare sans cesse et dans un pays habituellement silencieux.',
        points: [
          'Le score d’anomalie est l’écart à la ligne de base de chaque pays.',
          'Les signaux anciens contribuent de moins en moins avec le temps (décroissance à demi-vie).',
          '« Mesuré et jugé normal » est distingué de « aucune donnée pour juger » — les confondre fait lire les périodes calmes comme des alertes.',
        ],
      },
      {
        title: '04 · Prévoir',
        body: 'Des modèles de transmission estiment l’ampleur de la propagation et le risque d’importation. Chaque valeur porte ses hypothèses et ses limites.',
        points: [
          'Les modèles sont ajustés avec le R0 et la létalité propres à chaque maladie, issus de la littérature.',
          'Pour les pathogènes qui n’ont jamais provoqué d’épidémie généralisée, la **population atteignable** est limitée. Un R0 supérieur à 1 ne signifie pas que toute la population est infectée.',
          'Les estimations de décès modélisées sont confrontées automatiquement aux plus grandes épidémies connues ; lorsqu’une valeur dépasse l’intervalle explicable, **un avertissement accompagne le chiffre.**',
        ],
        note: 'Les chiffres de scénario sont des estimations sous hypothèses de modèle — ni des mesures, ni des garanties.',
      },
      {
        title: '05 · Répondre',
        body: 'Nous ne nous arrêtons pas à « ce qui arrive ». Les scénarios sans réponse et avec intervention sont comparés pour montrer quelles mesures maîtrisent la transmission.',
        items: [
          { title: 'Par rapport à l’absence de réponse', body: 'La trajectoire sans aucune mesure sert de référence.' },
          { title: 'Comparer les interventions', body: 'Des combinaisons d’isolement, de distanciation, de vaccination et de traitement sont testées pour trouver le point où le nombre de reproduction effectif passe sous 1.' },
          { title: 'Scellement', body: 'Prévisions et scénarios sont scellés par une empreinte au moment de leur production. Cela ne prouve pas qu’ils étaient justes, mais que nous détenions ce contenu à ce moment-là.' },
        ],
      },
    ],
    cta: {
      title: 'Le système en marche est plus parlant qu’une description',
      body: 'Vous pouvez ouvrir dès maintenant l’écran où ces cinq étapes tournent réellement.',
      label: 'Ouvrir le tableau de bord',
      href: '/dashboard',
    },
  },

  techSpec1: {
    metaTitle: 'Technologie I — la couche de veille permanente',
    metaDescription:
      'Les moteurs qui tournent automatiquement chaque heure : veille de la presse en langue locale, indice d’anomalie à six couches, veille des silences de déclaration, foyers inexpliqués, détection d’aberration CDC EARS et veille des défaillances silencieuses. La méthode et les limites de chaque moteur, énoncées clairement.',
    eyebrow: 'TECHNOLOGY · I',
    title: 'La couche de veille permanente',
    lead: 'Parmi les 114 modules algorithmiques d’AEGIRON, voici ceux qui tournent d’eux-mêmes chaque heure, sans qu’on le demande. Leur rôle : compter sans cesse ce qui s’écarte de la normale. Pour chaque moteur, nous indiquons ce qu’il prend comme référence et ce qu’il refuse délibérément de compter.',
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
        note: 'Les flux à données trop rares sont mis à part comme « indéterminés », non élevés en alertes. Nous ne passons pas en silence sur le fait que les données sont minces.',
      },
      {
        title: 'Indice d’anomalie à six couches',
        body: 'Les signaux de six couches — officielle, officieuse, comportementale, environnementale, animale et inexpliquée — sont convertis en scores d’anomalie par rapport à leur niveau habituel, pondérés par la fiabilité de la source, puis combinés en un seul indice. La référence est la ligne de base de chaque indicateur, non son volume absolu : un même décompte n’a pas le même sens dans un pays qui déclare beaucoup et dans un pays habituellement silencieux.',
        points: [
          'Chaque signal est scoré comme un écart (z-score) à sa propre distribution historique, la dernière valeur étant exclue de la ligne de base.',
          'Chaque couche porte une pondération de fiabilité différente — une API gouvernementale officielle et un décompte de publications sociales ne peuvent peser pareil.',
          'Les signaux anciens contribuent de moins en moins avec le temps (décroissance à demi-vie).',
        ],
        note: 'Cet indice ne regarde que les hausses. La baisse — un canal qui se tait — est traitée par la veille des silences ci-dessous.',
      },
      {
        title: 'Veille des silences de déclaration',
        body: 'Les signaux qui montent ne sont pas les seuls dangereux. Quand un canal de déclaration habituellement actif se tait soudain, c’est en soi un signal — le système de déclaration a pu s’effondrer. Lors d’Ebola en Guinée en 2014, les déclarations du ministère ont chuté d’abord ; des semaines après que l’OMS l’eut lu comme « calme », l’épidémie a explosé.',
        points: [
          'Un canal est retenu quand la valeur du jour tombe sous la moitié de sa moyenne historique.',
          'Seuls les indicateurs dotés d’une règle de décision explicitement déclarée sont surveillés — une conception par liste d’autorisation, pour qu’un « 0 » issu d’un rapport non encore déposé ne soit pas pris pour un effondrement.',
        ],
        note: 'Cette conception résulte d’une refonte après que la couche eut émis quatre fausses alertes lors du rodage d’avant-lancement en 2026-09. Nous avons gardé l’échec au dossier et l’avons corrigé.',
      },
      {
        title: 'Foyers inexpliqués',
        body: 'Parmi les foyers extraits de la presse, nous comptons à part ceux qui ne correspondent à aucun profil de maladie connu. Le foyer de pneumonie d’origine inconnue de Wuhan, en décembre 2019, en est l’archétype — l’objectif est de saisir « ceci ne ressemble pas au reste » avant que cela n’ait un nom.',
        points: [
          'Au moment de l’extraction, nous demandons directement au modèle de langage si le cas correspond à un profil de maladie connu. Nous ne forçons pas un cas dans la catégorie « inexpliqué » au seul motif qu’il manque à un petit dictionnaire d’alias.',
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
      'Les moteurs profonds qui tournent à la demande ou sur alerte : naturel de l’ordre des séquences mesuré, détection de chimères par homologie, simulation de propagation entre pays, estimation de la date d’importation, scénarios d’intervention par alerte, évaluation automatique des prévisions et scellement des prévisions — chacun avec sa base mesurée et ses limites.',
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
          'Mesuré (2026-07) : les séquences naturelles concordent étroitement, et mélanger l’ordre à composition identique fait chuter la concordance — cela saisit l’angle que les statistiques de composition ne peuvent voir.',
          'Il produit une « priorité d’examen complémentaire », non un verdict. Une faible concordance ne signifie pas à elle seule une séquence conçue.',
        ],
        note: 'Ce modèle a exclu de son entraînement les virus à hôte eucaryote ; il n’est donc pas appliqué aux séquences de coronavirus, de grippe ou d’Ebola — le domaine applicable est déclaré, et hors de celui-ci le score est rapporté sans qu’aucun signalement ne soit levé.',
      },
      {
        title: 'Génomique — détection de chimères par homologie',
        body: 'Pour éviter l’angle mort d’un modèle entraîné (les taxons laissés hors de l’entraînement), nous recherchons une séquence protéique dans des bases d’homologie publiques pour voir si une protéine naturelle couvre toute la longueur de la requête. Pour une protéine naturelle, des proches couvrent toute l’étendue ; pour une séquence assemblée à partir de fragments de plusieurs organismes, aucune protéine naturelle ne la couvre entièrement — la trace directe d’une recombinaison.',
        points: [
          'Comme il s’agit d’une recherche en base et non d’un modèle, elle fonctionne aussi sur les virus.',
          'Les seuils ont été pré-enregistrés pour qu’un test de faux positifs — incluant délibérément des pathogènes peu étudiés — soit passé.',
        ],
        note: 'Une faible couverture est une priorité d’examen « non entièrement expliqué par des homologues naturels », non un verdict d’artificialité. Le jugement final requiert un expert, de la phylogénie et un travail de paillasse.',
      },
      {
        title: 'Simulation — propagation entre pays',
        body: 'Un modèle SEIR métapopulationnel avec 159 pays comme nœuds, et 1 671 paires de pays reliées par avion et 314 frontières terrestres comme arêtes. Il rapporte les pays non atteints pendant la période séparément des pays pour lesquels aucune voie n’est connue — « sûr » et « inconnu » ne sont pas le même mot.',
        items: [
          { title: 'Estimation de la date d’importation', body: 'À partir du trafic international de la ville d’origine, de la durée de vol et de la croissance exponentielle initiale, il estime les jours jusqu’à un premier cas importé et le risque par point d’entrée.', meta: 'Une estimation de modèle, non une date d’importation observée' },
          { title: 'Limites du réseau', body: 'Le réseau aérien repose sur des données de liaisons de 2014. La connexion entre deux pays change peu, mais les fréquences ont beaucoup changé, et le trafic terrestre est une estimation fondée sur la population.', meta: 'Exposé avec le résultat sous air_network_coverage' },
        ],
      },
      {
        title: 'Réponse — scénarios d’intervention par alerte',
        body: 'Jusqu’ici une alerte s’arrêtait à « ce qui arrive ». Le destinataire n’obtenait aucune réponse à « que faire ». Pour chaque nouvelle alerte critique ou élevée, nous exécutons une simulation SEIR de défense avec des paramètres propres à la maladie et joignons l’écart entre absence de réponse et intervention, en décès et en jours de saturation hospitalière — l’étape qui transforme un outil de prévision en outil de décision.',
        points: [
          'Les coefficients de transmission et les taux de létalité sont des valeurs représentatives de la littérature. Avant calibration au pathogène et à la région réels, ils sont une référence directionnelle — nous disons « N sous hypothèses de modèle », jamais « sauve N ».',
          'Pour une alerte où la maladie ne peut être identifiée, nous ne produisons aucun nombre. Un bilan inventé à partir de constantes génériques serait un nombre sans fondement.',
        ],
      },
      {
        title: 'Auto-vérification — évaluation et scellement',
        body: 'La prétention de « savoir avant les autres » n’est qu’un argument commercial s’il n’existe aucun moyen de la prouver. Nous avons donc mis la vérification dans le code. Les prévisions enregistrées sont évaluées chaque jour au regard des déclarations officielles qui suivent, et chaque prévision est scellée au moment où elle est faite.',
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
      title: 'La base mesurée des moteurs profonds',
      body: 'Les mesures par taxon de la couche génomique et les limites de réseau de la simulation sont exposées dans Technologie II.',
      label: 'Voir Technologie II',
      href: 'technology-advanced',
    },
  },


  transparency: {
    metaTitle: 'Validation et limites — ce qui n’est pas encore prouvé et les lacunes connues',
    metaDescription:
      'Tout ce qu’AEGIRON n’a pas encore validé, ses limites connues et ses lacunes de données — ainsi que les mécanismes par lesquels le système vérifie ses propres chiffres.',
    eyebrow: 'VALIDATION & LIMITS',
    title: 'Validation et limites',
    lead: 'En veille épidémiologique, l’échec le plus dangereux n’est pas une prévision fausse, mais une prévision invérifiable. Nous indiquons donc d’abord ce qui n’est pas encore validé et les limites connues, puis les mécanismes par lesquels le système vérifie ses propres chiffres.',
    blocks: [
      {
        title: 'Pas encore validé',
        accent: true,
        points: [
          '**Il n’existe pas d’historique validé de précision en détection précoce.** C’est pourquoi aucune affirmation du type « détecté plusieurs jours plus tôt » ne figure sur ce site.',
          'Le système est entré en pleine exploitation en 2026. Les performances sur des épidémies antérieures relèvent d’une **reconstitution rétrospective** et ne valent pas performance en temps réel.',
          'Les chiffres de scénario des modules de prévision sont des **estimations sous hypothèses de modèle** — ni des mesures, ni des garanties.',
          'Aucun organisme externe n’a encore validé le système de façon indépendante. Toutes les évaluations de performance à ce jour sont internes.',
        ],
        note: 'Ces éléments évoluent à mesure que l’historique d’exploitation s’étoffe. Lorsqu’ils changent, cette page est mise à jour.',
      },
      {
        title: 'Limites connues',
        items: [
          {
            title: 'Lacunes de collecte',
            body: 'Des signaux manquent pour certains pays et certaines périodes. Là où les données sont vides, aucun modèle ne peut prévoir une épidémie.',
            meta: 'Le système signale lui-même les périodes vides',
          },
          {
            title: 'Taux de fausses alertes',
            body: 'Dans la plage de performance actuelle, de nombreuses alertes ne débouchent pas sur une épidémie réelle. La lassitude face aux alertes est une cause réelle d’échec des systèmes d’alerte précoce.',
            meta: 'Les seuils relèvent de la politique opérationnelle, non d’une bonne réponse',
          },
          {
            title: 'Erreurs d’extraction automatique',
            body: 'Les chiffres lus dans les tableaux PDF peuvent être mal interprétés. Une confrontation au texte source est appliquée, mais elle n’est pas exhaustive.',
            meta: 'Les valeurs non confirmées sont signalées à part',
          },
          {
            title: 'Qualité de traduction',
            body: 'La traduction automatique des articles en langue locale a été testée puis écartée : en swahili et en amharique, des noms de maladies disparaissaient et des sens s’inversaient.',
            meta: 'La correspondance par mots-clés reste en place jusqu’à une alternative',
          },
        ],
      },
      {
        title: 'La vérification que le système effectue lui-même',
        body: 'Si les limites ne figurent que dans des documents, les chiffres s’en détachent et sont repris tels quels à l’écran et dans les rapports. La vérification est donc inscrite dans le code.',
        points: [
          '**Comparaison historique** — les estimations de décès modélisées sont confrontées automatiquement à la plus grande épidémie connue pour la maladie ; au-delà de dix fois ce chiffre, un avertissement « ne pas utiliser dans des documents externes » accompagne la réponse.',
          '**Distinguer les causes d’échec** — lorsqu’une épidémie est manquée, « le modèle l’a manquée » est distingué de « il n’y avait pas de données pour la voir ». Les confondre inverse le diagnostic.',
          '**Évaluation prospective** — la performance n’est évaluée que sur un avenir inconnaissable au moment de la prévision, jamais sur les données d’entraînement. Ajouter des variables améliore presque toujours les scores en échantillon.',
          '**Provenance** — lorsqu’un nom de maladie ou un pays provient du contexte plutôt que d’un tableau, son origine est enregistrée avec lui.',
        ],
      },
      {
        title: 'Pourquoi cette page existe',
        body: 'Une entreprise liée par des contrats clients peut difficilement exposer ses faiblesses. AEGIRON n’est pas encore liée de cette façon et peut donc exposer ses limites en premier — ce qui devient un fondement de confiance que la due diligence peut vérifier directement. La première chose que vérifient réassureurs et évaluateurs publics est si une organisation connaît précisément ses propres limites.',
      },
    ],
    cta: {
      title: 'Si vous relevez une erreur',
      body: 'Si un élément de cette page est inexact ou qu’une limite manque, signalez-le-nous. Nous le vérifierons et en tiendrons compte.',
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
        body: 'Les plus rapides et les plus bruitées. L’actualité ne bouge qu’après qu’un journaliste a écrit son article ; ces sources reçoivent donc une fiabilité faible et sont toujours lues au regard d’autres axes.',
        items: [
          { title: 'Presse en langue locale', body: 'Flux d’actualité agrégés pour 179 pays et langues ; les flux ambigus sont reclassés par un modèle de langage.', meta: 'Mise à jour à la source : horaire' },
          { title: 'NewsWatch', body: 'Tendances de l’actualité des grandes maladies infectieuses, lues dans des résultats de recherche web résumés.', meta: 'Mise à jour à la source : horaire' },
          { title: 'Tendances de recherche Naver', body: 'Ratios de recherche sur la grippe, la COVID-19 et Ebola en Corée.', meta: 'Mise à jour à la source : quotidienne' },
          { title: 'Mastodon', body: 'Nombre de personnes publiant sous des mots-clics liés à des maladies (fenêtre glissante de sept jours).', meta: 'Mise à jour à la source : horaire' },
          { title: 'Consultations Wikipédia', body: 'Consultations des articles liés à Ebola. La source est actuellement instable ; les valeurs n’arrivent que par intermittence.', meta: 'Mise à jour à la source : quotidienne · instable' },
          { title: 'Polymarket', body: 'Prix de marchés prédictifs sur une nouvelle pandémie — un jugement collectif, non une preuve.', meta: 'Mise à jour à la source : horaire' },
        ],
      },
      {
        title: 'Environnement, animaux et comportements de préparation',
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
        items: [
          { title: 'Suivi des lignées Nextstrain', body: 'Composition des lignées dominantes et apparition de nouvelles lignées dans les séquences publiques réanalysées. Les jeux de données qui ne sont plus mis à jour ne sont pas utilisés.', meta: 'Mise à jour à la source : variable selon le jeu' },
          { title: 'Données de contre-mesures VALHALLA', body: 'Documents publics sur la préparation en contre-mesures : liste de préqualification de l’OMS, ClinicalTrials.gov et avis de marchés publics coréens (KONEPS). La connexion aux marchés publics européens (TED) n’est pas encore vérifiée et n’entre dans aucun décompte.', meta: 'Mise à jour à la source : quotidienne et mensuelle' },
        ],
      },
      {
        title: 'Sources retirées du suivi',
        body: 'Une source qui disparaît en silence est la défaillance la plus dangereuse d’un système de veille. Les sources retirées de l’exploitation restent donc listées, avec la raison.',
        items: [
          { title: 'Mobilité aérienne (OpenSky)', body: 'L’accès depuis les serveurs cloud est bloqué : la réception n’était pas fiable et la source a été retirée du suivi. La simulation de propagation entre pays utilise à part des données publiques de liaisons aériennes.', meta: 'Retirée du suivi' },
          { title: 'GroqWatch', body: 'Remplacée par NewsWatch en raison d’un taux d’échec élevé.', meta: 'Retirée du suivi · 2026-09-01' },
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
        title: 'Couche 1 · Collecte',
        body: 'Vingt-trois sources de collecte de natures très différentes sont normalisées dans un format de signal unique. La fiabilité variant selon l’origine, chaque valeur est conservée avec sa fiabilité, utilisée comme pondération dans tous les calculs ultérieurs.',
      },
      {
        title: 'Couche 2 · Extraction',
        body: 'Des chiffres structurés sont extraits de documents non structurés (tableaux PDF et texte d’articles). Les images de documents sont interprétées bloc par bloc, et les chiffres extraits sont confrontés au texte source. Les valeurs qui ne peuvent y être confirmées sont marquées comme non vérifiées.',
      },
      {
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
        body: 'Nous réunissons la presse en langue locale de 179 pays, les données officielles de surveillance et les signaux environnementaux, commerciaux et génomiques en un seul indice, jugeons l’anomalie de chaque pays au regard de sa propre ligne de base et — dès qu’une alerte est émise — calculons à côté les scénarios de propagation et les effets d’intervention. L’axe de conception est de ne pas s’arrêter à la détection mais de répondre à « et alors, et à quelle intensité ».',
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
          'Aucun organisme externe n’a encore validé le système de façon indépendante. Toutes les évaluations de performance à ce jour sont internes.',
          'Nous ne détenons aucun historique validé de détection précoce. Avec une exploitation continue, il s’accumule de lui-même, sous forme de prévisions scellées.',
        ],
      },
      {
        title: 'Pourquoi nous publions tout',
        body: 'Si, sans client ni contrat, on construit des choses à cacher, elles deviennent toutes des passifs au moment d’être validé. Tout ouvrir maintenant, c’est rester prêt à être vérifié. C’est aussi un choix qu’un concurrent de grande taille ne peut structurellement copier — il a des contrats clients à protéger ; nous pouvons ouvrir parce que nous n’en avons aucun. La faiblesse et la force viennent du même endroit.',
        note: 'Notre état de validation et nos limites connues sont exposés intégralement sur une page dédiée.',
      },
      {
        title: 'Où nous allons',
        items: [
          { title: 'Court terme', body: 'Nous connecter à des organisations de terrain et des réseaux de surveillance réels pour nous rapprocher de la source du signal. Réassureurs, gouvernements, organismes internationaux et organisations de terrain sont les premiers partenaires candidats.' },
          { title: 'Moyen terme', body: 'Poursuivre l’exploitation pour accumuler un historique de prévisions vérifiable. Le registre scellé est le fondement du « nous l’avions bien prévu, alors ».' },
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
