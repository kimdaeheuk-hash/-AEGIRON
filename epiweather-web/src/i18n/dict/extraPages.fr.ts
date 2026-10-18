import type { ExtraDict } from '../types';

/** Pages d’exploitation, de vérification et nationales (français). Valeurs mesurées uniquement. */
export const extraPagesFr: ExtraDict['pages'] = {
  live: {
    metaTitle: 'En exploitation — ce que fait AEGIRON en ce moment',
    metaDescription: 'Captures du tableau de bord d’AEGIRON en fonctionnement et chiffres d’exploitation en direct : ce qu’il collecte, où il regarde et ce qu’il a élevé en alerte.',
    eyebrow: 'LIVE OPERATIONS',
    title: 'Voici AEGIRON, en fonctionnement',
    lead: 'Pas une description : les écrans et les chiffres d’exploitation. Les chiffres et listes ci-dessous sont relus sur le serveur de production toutes les quelques minutes, et les images sont capturées sur le tableau de bord en fonctionnement.',
    blocks: [],
    cta: {
      title: 'Ouvrez vous-même le même écran',
      body: 'Le tableau de bord de production s’ouvre sans connexion et se met à jour en temps réel, comme sur les captures ci-dessus.',
      label: 'Ouvrir le tableau de bord',
      href: '/dashboard',
    },
  },

  record: {
    metaTitle: 'Registre public des prévisions — prévisions scellées et évaluations',
    metaDescription: 'AEGIRON publie ses prévisions telles qu’elles ont été faites : preuves d’horodatage sur la blockchain, évaluation automatique face aux déclarations officielles et registre d’antériorité, à partir de données réelles.',
    eyebrow: 'TRACK RECORD',
    title: 'Registre public des prévisions',
    lead: 'La confiance dans l’alerte précoce ne vient pas des affirmations. AEGIRON scelle une prévision au moment où elle est faite et l’évalue automatiquement chaque jour face aux déclarations officielles qui suivent. Succès, échecs et prévisions en attente ne sont jamais effacés : ils restent tels quels dans ce registre.',
    blocks: [],
    cta: {
      title: 'Comment l’évaluation fonctionne-t-elle ?',
      body: 'Ce qui compte comme vérité terrain — et ce qui n’en est jamais — est exposé sur la page de validation.',
      label: 'Voir le cadre de validation',
      href: 'transparency',
    },
  },

  korea: {
    metaTitle: 'AEGIRON pour la Corée — alerte précoce pour un pays d’arrivée',
    metaDescription: 'Moment d’importation des foyers étrangers et risque par point d’entrée, veille des maladies à déclaration obligatoire, souveraineté de production des contre-mesures, veille des marchés publics et souveraineté des données : AEGIRON du point de vue coréen.',
    eyebrow: 'FOR KOREA',
    title: 'AEGIRON pour la Corée',
    lead: 'Pour la plupart des infections émergentes, la Corée n’est pas le point de départ mais le point d’arrivée. La question est donc moins « où cela a-t-il commencé » que « quand, par quelle porte, et avec quoi l’arrêter ». AEGIRON a été conçu autour de cette question.',
    photo: {
      src: '/media/live/model-global-inflow.jpg',
      alt: 'Écran de détection des importations d’AEGIRON — carte du réseau aérien de l’origine jusqu’à la Corée',
      caption: 'L’écran de détection des importations du tableau de bord en fonctionnement (capture). Il estime le moment d’arrivée et le point d’entrée depuis une origine jusqu’en Corée ; les chiffres sont un scénario de modèle selon les hypothèses choisies.',
      credit: 'Écran d’exploitation AEGIRON',
      sourceUrl: '/dashboard',
    },
    blocks: [
      {
        title: 'Foyer étranger → importation nationale',
        kicker: 'INBOUND',
        tone: 'indigo',
        body: 'À partir du trafic international de la ville d’origine, de la durée de vol et de la croissance initiale, il estime les jours jusqu’à une première importation et répartit le risque par point d’entrée — Incheon, Gimhae, Gimpo et autres. Il poursuit ensuite sur le réseau de mobilité national jusqu’au moment d’arrivée par région.',
        specs: [
          { label: 'Première importation', value: 'J+jours selon l’origine (scénario de modèle)' },
          { label: 'Points d’entrée', value: 'Part par porte — Incheon · Gimhae (Busan) · Gimpo et autres' },
          { label: 'Propagation nationale', value: 'Moment d’arrivée par province (modèle métapopulationnel)' },
          { label: 'Contexte mondial', value: 'Jumeau de propagation sur 159 pays · 1 671 liaisons aériennes · 314 frontières terrestres' },
        ],
      },
      {
        title: 'Veille nationale',
        kicker: 'DOMESTIC',
        tone: 'teal',
        items: [
          { title: 'Flambées par maladie à déclaration', body: 'Lit les déclarations hebdomadaires de la KDCA maladie par maladie, pour saisir les flambées qu’un total masquerait.', meta: 'kdca_anomaly' },
          { title: 'Signal de recherche national', body: 'Suit l’intérêt national pour la grippe, la COVID-19, Ebola et d’autres via Naver DataLab.', meta: 'naver_trends' },
          { title: 'Briefing quotidien en coréen', body: 'Un briefing en coréen sur la situation nationale et mondiale, généré chaque jour.', meta: 'daily_brief' },
        ],
      },
      {
        title: 'Souveraineté de production des contre-mesures (VALHALLA)',
        kicker: 'SOVEREIGNTY',
        tone: 'forest',
        body: 'À partir de sources publiques, il compte, menace par menace, s’il existe un moyen de l’arrêter et si ce moyen peut être produit dans le pays. Un produit à fournisseur étranger unique est un goulet d’étranglement : en crise, le stock ne peut être reconstitué.',
        points: [
          'La couverture par menace est calculée à partir des stocks d’urgence internationaux et des produits autorisés.',
          'La liste de préqualification de l’OMS donne le nombre de fournisseurs capables de produire chaque produit.',
          'ClinicalTrials.gov décompose « encore en développement » jusqu’à la phase d’essai.',
        ],
      },
      {
        title: 'Veille des marchés publics',
        kicker: 'PROCUREMENT',
        tone: 'amber',
        body: 'Chaque jour, il suit les achats liés à la biosécurité et aux épidémies dans le système coréen d’appels d’offres publics (KONEPS). Ce que l’État prépare apparaît d’abord dans les appels d’offres.',
      },
      {
        title: 'Souveraineté des données',
        kicker: 'DATA SOVEREIGNTY',
        tone: 'violet',
        body: 'Le chemin d’extraction des signaux est conçu pour basculer, en un seul endroit, vers un modèle auto-hébergé, afin que les données sensibles n’aient pas à partir vers des API étrangères. Les détails figurent sur la page sécurité et gouvernance des données.',
      },
    ],
    cta: {
      title: 'Comment les organismes publics s’engagent',
      body: 'Les étapes, de la revue initiale au cadrage, au pilote et à l’évaluation conjointe, sont exposées.',
      label: 'Voir les modalités',
      href: 'pilot',
    },
  },

  security: {
    metaTitle: 'Sécurité et gouvernance des données',
    metaDescription: 'Contrôle d’accès d’AEGIRON, audit des programmes à haut risque, principes de confidentialité, voie de souveraineté des données, gestion des secrets et intégrité d’exploitation.',
    eyebrow: 'SECURITY & GOVERNANCE',
    title: 'Sécurité et gouvernance des données',
    lead: 'Le renseignement sur les maladies infectieuses touche à la sécurité publique. Qui peut modifier quoi, comment les fonctions sensibles sont contrôlées et où vont les données — décrit exactement tel que c’est implémenté dans le code.',
    blocks: [
      {
        title: 'Contrôle d’accès',
        kicker: 'ACCESS CONTROL',
        tone: 'indigo',
        specs: [
          { label: 'API au total', value: '123 points d’accès' },
          { label: 'Authentification requise', value: '37 — fonctions modifiant l’état, coûteuses ou à haut risque' },
          { label: 'Méthode', value: 'En-tête X-API-Key · plusieurs clés étiquetées · comparaison à temps constant' },
          { label: 'Sans clé configurée', value: 'Toutes les API d’écriture désactivées — jamais laissées ouvertes' },
        ],
        note: 'Les API de lecture renvoient des données publiques traitées et sont publiques. Tout appel qui modifie des données ou engage un coût exige une clé.',
      },
      {
        title: 'Contrôle des programmes à haut risque',
        kicker: 'HEIMDALL · VALHALLA',
        tone: 'violet',
        points: [
          'Les programmes internes du plus haut niveau (HEIMDALL et autres) exigent une authentification, et chaque appel est conservé dans un journal d’audit par étiquette de clé.',
          'HEIMDALL est **réservé à la détection défensive.** Il n’a aucune fonction de conception, de synthèse, d’optimisation ou de contournement de séquences.',
          'La diffusion externe ou la redistribution des résultats exige une approbation, et la réponse l’indique.',
        ],
      },
      {
        title: 'Principes de confidentialité',
        kicker: 'PRIVACY',
        tone: 'teal',
        points: [
          'Ce qui est collecté est public : rapports des autorités sanitaires, couverture de presse et statistiques publiques. Aucune donnée individuelle de patient n’est traitée.',
          'Le site et le tableau de bord fonctionnent sans connexion, sans publicité ni outil de suivi des visiteurs.',
        ],
      },
      {
        title: 'Souveraineté des données',
        kicker: 'SOVEREIGNTY',
        tone: 'forest',
        body: 'La couche de modèle chargée de l’extraction des signaux est conçue pour changer de fournisseur en un seul endroit, et peut donc passer à un modèle auto-hébergé (y compris sur site). Un organisme national peut l’exploiter sans envoyer de données sensibles à des API externes.',
      },
      {
        title: 'Gestion des secrets et intégrité d’exploitation',
        kicker: 'INTEGRITY',
        tone: 'sky',
        items: [
          { title: 'Gestion des secrets', body: 'Les clés d’API et identifiants ne vivent que dans les variables d’environnement de production — jamais dans le dépôt ni dans les documents.' },
          { title: 'Porte de mise en production', body: 'Seul le code qui passe les 2 145 tests automatisés est mis en production.' },
          { title: 'Veille des défaillances silencieuses', body: 'La santé des sources et les invariants de qualité contrôlent à chaque cycle l’intégrité de la collecte et du calcul.' },
          { title: 'Preuve d’intégrité', body: 'Les prévisions sont scellées par empreinte et leur horodatage ancré sur la blockchain Bitcoin.' },
        ],
      },
    ],
    cta: {
      title: 'Besoin de documents pour une revue de sécurité ?',
      body: 'Vous pouvez demander une description de l’architecture et des contrôles pour une revue de sécurité institutionnelle.',
      label: 'Nous contacter',
      href: 'contact',
    },
  },

  press: {
    metaTitle: 'Kit média',
    metaDescription: 'Une description d’AEGIRON en une ligne et en un paragraphe, les faits clés, la vidéo de présentation et les règles d’usage des images.',
    eyebrow: 'PRESS',
    title: 'Kit média',
    lead: 'Des éléments utilisables tels quels pour présenter AEGIRON dans un article, une intervention ou un rapport. Chaque chiffre est mesuré ; aucune affirmation de précision ni de délai d’avance.',
    blocks: [
      {
        title: 'En une ligne',
        kicker: 'ONE-LINER',
        tone: 'teal',
        body: 'AEGIRON est un système mondial d’alerte précoce sur les maladies infectieuses, basé à Busan (Corée du Sud), qui analyse chaque heure la presse locale de 178 pays en 52 langues et les données officielles de surveillance pour juger les anomalies et calculer des scénarios de propagation et de réponse.',
      },
      {
        title: 'Présentation',
        kicker: 'BOILERPLATE',
        tone: 'indigo',
        body: 'AEGIRON vise à saisir le signal avant qu’une épidémie ne devienne une actualité internationale. Avec 23 sources de données et 114 modules algorithmiques, il juge les anomalies par pays et, dès qu’une alerte est émise, calcule en parallèle une simulation de propagation sur 159 pays et des scénarios d’intervention. Chaque prévision est scellée sur la blockchain à sa création et évaluée automatiquement face aux déclarations officielles ultérieures ; le système, la méthodologie, les données et les limites sont ouverts dès le départ. Deux programmes de R&D — criblage génomique défensif (HEIMDALL) et préparation en contre-mesures (VALHALLA) — portent l’axe de biosécurité nationale.',
      },
      {
        title: 'Faits clés',
        kicker: 'FACT SHEET',
        tone: 'sky',
        specs: [
          { label: 'Siège', value: 'Busan, Corée du Sud' },
          { label: 'Portée de veille', value: '178 pays · 52 langues de presse locale' },
          { label: 'Sources de données', value: '23 · collectées chaque heure' },
          { label: 'Modules algorithmiques', value: '114' },
          { label: 'API publique', value: '123 points d’accès' },
          { label: 'Ce qui est ouvert', value: 'Système · méthodologie · sources · limites · registre des prévisions' },
        ],
        note: 'Mesuré au 2026-10-18. Merci de citer avec la date.',
      },
      {
        title: 'Vidéo et images',
        kicker: 'ASSETS',
        tone: 'forest',
        items: [
          { title: 'Vidéo de présentation', body: 'Vous pouvez lier la vidéo de présentation d’AEGIRON (YouTube) de la page d’accueil.', meta: 'youtu.be/2Uzl-5JgLjs' },
          { title: 'Écrans d’exploitation', body: 'Les captures du tableau de bord de la page d’exploitation peuvent être utilisées avec la mention AEGIRON.', meta: '/live' },
          { title: 'Photos publiques', body: 'Les photos de terrain de ce site sont des œuvres du domaine public ou sous licence libre de leurs auteurs. Respectez la source et la licence de chaque photo.', meta: 'Crédit indiqué par photo' },
        ],
      },
    ],
    cta: {
      title: 'Demandes presse et interviews',
      body: 'Contactez-nous si vous avez besoin d’autres éléments ou d’une interview.',
      label: 'Nous contacter',
      href: 'contact',
    },
  },

  pilot: {
    metaTitle: 'Modalités — de la revue au pilote',
    metaDescription: 'Travailler avec AEGIRON se fait en cinq étapes : revue du système ouvert, cadrage, exploitation pilote, évaluation conjointe et extension.',
    eyebrow: 'HOW TO ENGAGE',
    title: 'Modalités',
    lead: 'Vous pouvez d’abord examiner l’ensemble du système sans réserver de démonstration. Le pilote qui suit est conçu pour démarrer sans aucune de vos données.',
    blocks: [
      {
        title: 'Cinq étapes',
        kicker: 'PROCESS',
        tone: 'indigo',
        items: [
          { title: '01 · Revue initiale', body: 'Consultez d’abord le tableau de bord, la méthodologie, les sources et le registre des prévisions. La revue n’exige aucun contrat.', meta: 'En autonomie' },
          { title: '02 · Cadrage', body: 'Nous convenons ensemble des pays et maladies d’intérêt, des canaux d’alerte (Telegram, e-mail), des formats de livrables et des critères d’évaluation.', meta: 'Conception conjointe' },
          { title: '03 · Exploitation pilote', body: 'Pendant une période convenue, vous recevez alertes, briefings et rapports de risque par pays sur mesure et les mettez à l’épreuve.', meta: 'Période convenue' },
          { title: '04 · Évaluation conjointe', body: 'Les alertes et prévisions du pilote sont évaluées ensemble face aux déclarations officielles, directement depuis l’enregistrement scellé.', meta: 'Enregistrement non modifiable' },
          { title: '05 · Extension', body: 'Le périmètre, l’intégration (API) et le mode d’exploitation s’élargissent selon l’évaluation.', meta: 'Fondé sur l’évaluation' },
        ],
      },
      {
        title: 'Ce que vous recevez',
        kicker: 'DELIVERABLES',
        tone: 'teal',
        points: [
          'Alertes sur mesure — les alertes Critiques et Élevées de votre périmètre, en temps réel',
          'Rapports de risque par pays — preuves de signal, vulnérabilité et potentiel de propagation',
          'Scénarios d’intervention — absence de réponse face à intervention, par alerte (étiquetés comme scénarios de modèle)',
          'Briefings quotidiens et accès API',
        ],
      },
      {
        title: 'Ce qu’il vous faut',
        kicker: 'WHAT YOU NEED',
        tone: 'forest',
        points: [
          'Les pays et maladies d’intérêt, et l’objectif',
          'Un contact et un canal d’alerte',
          'Aucune donnée client n’est requise — tout part de sources publiques.',
        ],
        note: 'La durée et les conditions se définissent selon le périmètre.',
      },
    ],
    cta: {
      title: 'Commencez par la revue',
      body: 'Après la revue, contactez-nous avec vos questions ou une proposition de pilote.',
      label: 'Nous contacter',
      href: 'contact',
    },
  },

  developers: {
    metaTitle: 'Développeurs · API',
    metaDescription: 'L’API REST d’AEGIRON — 123 points d’accès, réponses JSON, authentification X-API-Key et documentation OpenAPI. Guide d’intégration aux systèmes institutionnels.',
    eyebrow: 'DEVELOPERS',
    title: 'Développeurs · API',
    lead: 'Chaque valeur affichée par le tableau de bord provient de la même API REST. Vous pouvez intégrer alertes, indices de risque et briefings directement dans un système institutionnel.',
    blocks: [
      {
        title: 'Informations de base',
        kicker: 'BASICS',
        tone: 'sky',
        specs: [
          { label: 'URL de base', value: 'https://epiweather-api-production.up.railway.app' },
          { label: 'Format', value: 'REST · JSON' },
          { label: 'Authentification', value: 'Lecture publique · écriture/haut risque via X-API-Key' },
          { label: 'Documentation interactive', value: '/docs (OpenAPI)' },
        ],
      },
      {
        title: 'Points d’accès fréquents',
        kicker: 'QUICK START',
        tone: 'teal',
        items: [
          { title: 'Classement des risques par pays', body: 'Classement complet du risque final par pays (risque brut × vulnérabilité).', meta: 'GET /api/risk-index' },
          { title: 'Alertes', body: 'Candidates actuelles après classement et plafonds quotidiens.', meta: 'GET /api/alerts' },
          { title: 'Briefing quotidien', body: 'Le briefing quotidien de situation par langue.', meta: 'GET /api/daily-brief?lang=fr' },
          { title: 'Registre des prévisions', body: 'Prévisions scellées et tableau d’évaluation.', meta: 'GET /api/predictions · /scorecard' },
          { title: 'Preuve d’horodatage', body: 'État de la preuve d’horodatage blockchain par prévision.', meta: 'GET /api/predictions/{id}/timestamp-proof' },
          { title: 'État d’exploitation', body: 'Santé des sources, volume de données et état du planificateur.', meta: 'GET /api/status' },
        ],
      },
    ],
    cta: {
      title: 'Besoin d’une clé d’intégration ?',
      body: 'Nous délivrons des clés d’API par institution pour les intégrations en écriture et à haut risque.',
      label: 'Nous contacter',
      href: 'contact',
    },
  },

  diseases: {
    metaTitle: 'Veille par maladie',
    metaDescription: 'Les principales infections surveillées par AEGIRON — grippe aviaire H5N1, Ebola, Marburg, mpox, choléra, rougeole, MERS et Nipah : ce qui est surveillé pour chacune et les paramètres des simulations.',
    eyebrow: 'DISEASES',
    title: 'Veille par maladie',
    lead: 'Même au sein d’un seul système d’alerte, le signal qui bouge en premier diffère selon la maladie. Pour les principales infections, voici ce qu’AEGIRON surveille et quels paramètres de la littérature sa simulation de propagation utilise.',
    blocks: [],
    cta: {
      title: 'Voyez les signaux de chaque maladie',
      body: 'Les derniers signaux par maladie sont sur le tableau de bord et dans les briefings quotidiens.',
      label: 'Ouvrir le tableau de bord',
      href: '/dashboard',
    },
  },
};
