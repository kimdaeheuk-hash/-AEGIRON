import type { Dictionary } from '../types';
import { pagesFr } from './pages.fr';

/**
 * Dictionnaire français — choisi parce que les régions que le système couvre
 * réellement sont francophones (RDC, Guinée, Tchad, République centrafricaine).
 * Les langues de travail de l’OMS AFRO sont l’anglais et le français, et MSF
 * est basé à Genève et Paris.
 *
 * ★ RÈGLE ABSOLUE ★ Aucune affirmation de précision ni de délai d’avance.
 * « détecté N jours plus tôt », « précision de N % », « N épidémies prédites »
 * sont interdits : nous n’avons pas d’historique validé, et une due diligence
 * le mettrait immédiatement en évidence. Uniquement des faits mesurables :
 * l’échelle de l’infrastructure, ce que nous publions, et ce que nous ignorons.
 */
export const fr: Dictionary = {
  pages: pagesFr,

  briefings: {
    archiveTitle: 'Bulletins précédents',
    count: '{n} bulletins',
    quietDay: 'Journée calme',
    openBrief: 'Lire',
    empty: 'Aucun bulletin n’a encore été archivé.',
    error: 'Les bulletins n’ont pas pu être chargés. Le système, lui, fonctionne toujours.',
    backToList: 'Tous les bulletins',
    summary: 'Résumé',
    segments: 'Rubriques',
    ticker: 'Fil d’actualité',
    disclosure: 'Avertissement',
    notFound: 'Aucun bulletin pour cette date.',
    langNoticeTitle: 'Remarque sur la langue',
    langNoticeMismatch:
      'Ce bulletin a été généré dans une langue différente de celle demandée. Nous l’affichons tel quel plutôt que de masquer cet écart.',
  },

  common: {
    siteName: 'AEGIRON',
    siteTagline: 'Veille et alerte précoce des maladies infectieuses',
    readMore: 'En savoir plus',
    backToHome: 'Retour à l’accueil',
    lastUpdated: 'Dernière mise à jour',
    liveNow: 'En direct',
  },

  nav: {
    platform: 'Système',
    technology: 'Technologie',
    programs: 'Programmes spéciaux',
    methodology: 'Méthodologie',
    transparency: 'Validation et limites',
    dataSources: 'Sources de données',
    solutions: 'Cas d’usage',
    briefings: 'Bulletins',
    about: 'À propos',
    contact: 'Contact',
    dashboard: 'Tableau de bord en direct',
    openMenu: 'Ouvrir le menu',
    closeMenu: 'Fermer le menu',
    language: 'Langue',
  },

  footer: {
    tagline: 'Avant qu’une épidémie ne devienne une actualité internationale.',
    product: 'Produit',
    company: 'Entreprise',
    legal: 'Mentions légales',
    privacy: 'Politique de confidentialité',
    terms: 'Conditions d’utilisation',
    rights: 'Tous droits réservés.',
    location: 'Busan, Corée du Sud',
    disclaimer:
      'AEGIRON ne dispose pas encore d’un historique validé en matière de précision de détection précoce. Tous les chiffres de ce site mesurent l’échelle du système, et non sa performance prédictive.',
  },

  home: {
    metaTitle: 'AEGIRON — Alerte précoce, prévision et simulation de la propagation des maladies infectieuses',
    metaDescription:
      'Un système de renseignement épidémiologique qui détecte les anomalies dans la presse en langue locale de 179 pays et dans les données officielles de surveillance, joint des scénarios d’intervention à chaque alerte et évalue chacune de ses prévisions au regard des déclarations officielles qui suivent.',

    heroLiveOk: 'Sources de données : {ok}/{total} en fonctionnement normal',
    heroLiveUnknown: 'L’état de la collecte n’a pas pu être vérifié pour l’instant',
    heroTitle: 'Au-delà de l’alerte :\n[[prévision]] et [[simulation]]',
    heroLead:
      'AEGIRON détecte les anomalies dans la presse en langue locale de 179 pays et dans les données officielles de surveillance, et calcule, dès qu’une alerte est émise, des scénarios de propagation pour chaque niveau d’intervention. Chaque prévision est évaluée automatiquement au regard des déclarations officielles qui suivent ; une prévision sans élément de comparaison n’est comptée ni comme un succès ni comme un échec.',
    heroPrimaryCta: 'Tableau de bord',
    heroSecondaryCta: 'Architecture des moteurs',
    heroNoLogin: 'Accès immédiat — sans inscription ni connexion',

    stats: [
      { value: '114', label: 'Modules algorithmiques', note: 'Détection · génomique · prévision · réponse · vérification' },
      { value: '123', label: 'Points d’accès API', note: 'Collecte · analyse · simulation · évaluation' },
      { value: '2 145', label: 'Tests automatisés', note: 'Tous doivent réussir avant toute mise en production' },
      { value: '179', label: 'Flux d’actualité en langue locale', note: 'Agrégés par pays et par langue, collectés toutes les heures' },
    ],
    statsAsOf: 'Mesuré le 2026-10-18 à partir du dépôt et des journaux de production',
    introVideoLabel: 'AEGIRON — présentation',
    photo: {
      src: '/media/photos/earth-eastern-hemisphere.jpg',
      alt: 'Hémisphère oriental de la Terre — Afrique, Europe et Asie (composite satellitaire)',
      caption: 'Hémisphère oriental de la Terre (Blue Marble). Un composite d’observations satellitaires.',
      credit: 'NASA · Domaine public',
      sourceUrl: 'https://commons.wikimedia.org/wiki/File:Blue_Marble_Eastern_Hemisphere.jpg',
      position: 'center 45%',
    },

    engineTitle: 'Les moteurs',
    engineLead:
      'Seize des 114 modules forment l’ossature de la détection, de la génomique, de la prévision, de la réponse et de la vérification. Chacun indique son mode de fonctionnement réel, afin qu’un moteur exécuté toutes les heures ne soit jamais présenté avec le même poids qu’un moteur qui ne calcule qu’à la demande.',
    engineModes: {
      hourly: 'Toutes les heures',
      daily: 'Quotidien',
      onAlert: 'À chaque alerte',
      onRequest: 'À la demande',
    },
    engineCaveatLabel: 'Limites',
    engineGroups: [
      {
        key: 'detect',
        label: 'Détection',
        engines: [
          {
            id: 'local_news',
            name: 'Veille de la presse en langue locale',
            body: 'Mesure la densité du vocabulaire épidémiologique dans l’actualité agrégée par pays et par langue, et reclasse les flux ambigus à l’aide d’un modèle de langage. La cible est le premier article local, avant toute couverture en anglais.',
            mode: 'hourly',
          },
          {
            id: 'gai',
            name: 'Indice d’anomalie à six couches',
            body: 'Convertit les signaux de six couches — officielle, officieuse, comportementale, environnementale, animale et inexpliquée — en scores d’anomalie par rapport à la ligne de base propre à chaque signal, les pondère par la fiabilité de la source et les combine en un indice unique. La référence est le niveau habituel de chaque indicateur, non son volume absolu.',
            mode: 'hourly',
          },
          {
            id: 'negative_space',
            name: 'Veille des silences de déclaration',
            body: 'Suit les canaux de déclaration qui tombent sous la moitié de leur ligne de base. Elle vise des situations comme Ebola en Guinée en 2014, où l’effondrement de la déclaration a précédé la propagation, et ne juge que les indicateurs dotés d’une règle de décision déclarée.',
            mode: 'hourly',
          },
          {
            id: 'unexplained',
            name: 'Foyers inexpliqués',
            body: 'Comptabilise à part les foyers extraits de la presse qui ne correspondent à aucun profil de maladie connu. La pneumonie d’origine inconnue de Wuhan, en décembre 2019, en est l’archétype.',
            mode: 'hourly',
          },
        ],
      },
      {
        key: 'genomics',
        label: 'Génomique',
        engines: [
          {
            id: 'genomic_variants',
            name: 'Suivi de la composition des clades',
            body: 'Lit, dans la réanalyse des séquences publiques par Nextstrain, l’évolution de la part du clade dominant et l’apparition de nouveaux clades — des changements de transmissibilité ou d’échappement immunitaire qui précèdent les nombres de cas. Les jeux de données qui ne sont plus mis à jour ne servent pas de signal.',
            mode: 'hourly',
          },
          {
            id: 'evo2_naturalness',
            name: 'Mesure du naturel de l’ordre des séquences',
            body: 'Fournit au modèle génomique de fondation Evo2 le seul début d’une séquence, lui fait prédire les bases suivantes et mesure la concordance avec la séquence réelle. Il vise les segments assemblés ou recombinés que les statistiques de composition ne révèlent pas.',
            mode: 'onRequest',
            caveat: 'Evo2 a exclu de son entraînement les virus à hôte eucaryote ; il n’est donc pas appliqué aux séquences de coronavirus, de grippe ou d’Ebola.',
          },
          {
            id: 'msa_homology',
            name: 'Détection de chimères par homologie',
            body: 'Interroge des bases d’homologie publiques pour vérifier si une protéine naturelle couvre toute la longueur de la séquence. S’agissant d’une recherche et non d’un modèle entraîné, la méthode s’applique aussi aux pathogènes qu’Evo2 ne traite pas.',
            mode: 'onRequest',
          },
        ],
      },
      {
        key: 'simulate',
        label: 'Prévision · Simulation',
        engines: [
          {
            id: 'forecast_engine',
            name: 'Tendance à 7 et 14 jours',
            body: 'Extrapole à 7 et 14 jours la série temporelle de chaque indicateur à l’aide d’un ensemble régression linéaire et lissage exponentiel, et publie le résultat dans le bulletin quotidien.',
            mode: 'daily',
            caveat: 'Une extrapolation de séries de signaux, et non un nombre de cas mesuré.',
          },
          {
            id: 'digital_twin',
            name: 'Simulation de la propagation entre pays',
            body: 'Un modèle SEIR métapopulationnel dont les nœuds sont 159 pays et les arêtes 1 671 paires de pays reliées par avion et 314 frontières terrestres. Il distingue les pays non atteints pendant la période de ceux pour lesquels aucune voie n’est connue.',
            mode: 'onRequest',
            caveat: 'Le réseau aérien repose sur des données de liaisons de 2014 ; le trafic terrestre est une estimation fondée sur la population.',
          },
          {
            id: 'global_inflow',
            name: 'Estimation de la date d’importation',
            body: 'Estime le nombre de jours avant un premier cas importé en Corée, ainsi que le risque par point d’entrée, à partir du trafic international de la ville d’origine, de la durée de vol et de la croissance exponentielle initiale.',
            mode: 'onRequest',
            caveat: 'Une estimation de modèle, et non une date d’importation observée.',
          },
        ],
      },
      {
        key: 'respond',
        label: 'Réponse',
        engines: [
          {
            id: 'alert_intervention',
            name: 'Scénarios d’intervention par alerte',
            body: 'Pour chaque nouvelle alerte critique ou élevée, exécute une simulation SEIR de défense avec des paramètres propres à la maladie et joint l’écart entre absence de réponse et intervention. L’alerte ne s’arrête plus à « ce qui arrive » : elle répond aussi à « quelle mesure change quoi ».',
            mode: 'onAlert',
            caveat: 'Un scénario de modèle fondé sur des paramètres de la littérature, et non une prévision. Aucun chiffre n’est produit lorsque la maladie ne peut être identifiée.',
          },
          {
            id: 'defense',
            name: 'Comparaison d’interventions dans le temps',
            body: 'Fait varier la date de début et l’intensité de l’isolement, de la distanciation et de la vaccination pour comparer l’évolution du nombre de reproduction effectif et des jours de saturation hospitalière.',
            mode: 'onRequest',
          },
        ],
      },
      {
        key: 'verify',
        label: 'Auto-vérification',
        engines: [
          {
            id: 'prediction_resolver',
            name: 'Évaluation automatique des prévisions',
            body: 'Confronte chaque jour les prévisions enregistrées aux déclarations officielles qui suivent et les classe en succès, échec ou indéterminé. Les pics de consultation et les mises à jour du nombre de cas ne servent jamais de vérité terrain : ce serait évaluer nos signaux avec nos propres signaux.',
            mode: 'daily',
          },
          {
            id: 'lead_time_ledger',
            name: 'Registre d’antériorité',
            body: 'Enregistre le moment où un signal a été vu pour la première fois, avant toute déclaration officielle. Une antériorité reconstituée a posteriori, après la déclaration, n’est pas acceptée comme mesure.',
            mode: 'hourly',
          },
          {
            id: 'prediction_timestamp',
            name: 'Scellement des prévisions',
            body: 'Ancre l’empreinte SHA-256 d’une prévision dans la blockchain Bitcoin via OpenTimestamps, afin qu’un tiers puisse vérifier lui-même que la prévision n’a pas été réécrite après coup.',
            mode: 'onRequest',
          },
          {
            id: 'source_health',
            name: 'Veille des défaillances silencieuses',
            body: 'Vérifie séparément, à chaque cycle, si chaque source a réellement livré des valeurs et si la méthode qui les produit tient toujours. Une source dont la collecte a tourné sans rien renvoyer n’est pas comptée comme saine.',
            mode: 'hourly',
          },
        ],
      },
    ],

    specialEyebrow: 'SPECIAL PROGRAMS',
    specialTitle: 'Deux axes qu’aucun concurrent n’a — HEIMDALL · VALHALLA',
    specialLead: 'La plupart des couches de veille opèrent à découvert. Mais deux programmes de R&D internes, de nature différente, portent l’axe de biosécurité nationale. Nous énonçons seulement ce qu’ils font et ne font pas, sans rien surévaluer.',
    specialCards: [
      { code: 'HEIMDALL', name: 'Criblage génomique défensif', body: 'Détecte et signale si une séquence s’écarte des statistiques de l’évolution naturelle. Aucune fonction de conception ou de synthèse — une priorité d’examen, non un verdict.' },
      { code: 'VALHALLA', name: 'Préparation en contre-mesures', body: 'Au lieu d’imiter une prédiction moléculaire, il agrège les écarts de couverture des stocks et de souveraineté de production à partir de données publiques. Il ne touche pas aux informations non publiques comme les quantités des stocks nationaux.' },
    ],
    specialCta: 'Voir les programmes spéciaux',

    openTitle: 'Ouvert, pour pouvoir être vérifié',
    openLead:
      'L’échec le plus courant en veille épidémiologique n’est pas une prévision fausse, mais une prévision invérifiable. Le système, la méthodologie, les données et les limites qui fondent chaque jugement sont donc ouverts dès le départ.',
    openItems: [
      {
        title: 'Le système en direct',
        body: 'Le tableau de bord montre les données opérationnelles de collecte et d’alerte telles qu’elles tournent. Dans la console de simulation, les valeurs supposées et modélisées sont signalées comme telles à l’écran.',
        href: '/dashboard',
        linkLabel: 'Ouvrir le tableau de bord',
      },
      {
        title: 'Méthodologie',
        body: 'Comment les signaux sont collectés, les anomalies jugées et les prévisions établies, en quatre couches — avec le standard que suit chacune.',
        href: '/methodology',
        linkLabel: 'Lire la méthodologie',
      },
      {
        title: 'Sources de données',
        body: 'Toutes les sources opérationnelles, sans exception, avec ce que chacune ne peut pas voir et son état en ce moment.',
        href: '/data-sources',
        linkLabel: 'Voir les sources',
      },
      {
        title: 'Validation et limites',
        body: 'Ce qui n’est pas encore validé, les limites et lacunes de données connues, et la façon dont le système vérifie ses propres chiffres.',
        href: '/transparency',
        linkLabel: 'Voir l’état de validation',
      },
    ],

    honestTitle: 'Nous vérifions nos chiffres en premier',
    honestLead:
      'La confiance dans un système d’alerte précoce vient de son processus de vérification, non de l’ampleur de ses affirmations. Voici ce que nous n’avons pas encore — et les mécanismes déjà en place pour combler cet écart.',
    honestPoints: [
      'Il n’existe **pas encore d’historique validé** de précision en détection précoce. C’est pourquoi nous ne prétendons jamais avoir « détecté plusieurs jours plus tôt ».',
      'En revanche, chaque prévision est **scellée au moment où elle est faite** et évaluée chaque jour au regard des déclarations officielles qui suivent. L’historique se constitue à partir de ce registre, non d’affirmations.',
      'Les chiffres de scénario sont présentés comme des **estimations de modèle sous hypothèses explicites** et confrontés automatiquement aux plus grandes épidémies connues — un avertissement accompagne toute valeur hors de cet intervalle.',
      'Les lacunes de données ne sont jamais masquées. Le système signale lui-même les pays et périodes vides, et les sources interrompues.',
    ],
    honestClose:
      'Quand une épidémie est manquée, nous distinguons « le modèle l’a manquée » de « il n’y avait pas de données pour la voir ». Confondre les deux inverse le diagnostic.',
    honestCta: 'Voir l’état de validation complet',

    pipelineTitle: 'Du signal à l’alerte',
    pipelineLead: 'Cinq étapes. À chacune, ce que nous écartons compte autant que ce que nous retenons.',
    pipelineSteps: [
      {
        step: '01',
        title: 'Collecter',
        body: 'Données officielles des bureaux régionaux de l’OMS et des autorités sanitaires nationales, presse en langue locale de 179 pays, sources académiques, surveillance des eaux usées et données de lignées génomiques — toutes les heures.',
      },
      {
        step: '02',
        title: 'Extraire',
        body: 'Maladie, pays, cas et décès sont structurés à partir des tableaux PDF et du texte des articles. Ce qui ne peut être lu reste vide et n’est jamais comblé par supposition.',
      },
      {
        step: '03',
        title: 'Juger',
        body: 'Les anomalies sont mesurées par rapport au niveau habituel de chaque indicateur, non en valeur absolue — les mêmes cinq cas n’ont pas le même sens d’un pays à l’autre.',
      },
      {
        step: '04',
        title: 'Prévoir',
        body: 'Des modèles de transmission estiment les voies de propagation et le risque d’importation, et chaque valeur porte ses hypothèses et ses limites.',
      },
      {
        step: '05',
        title: 'Répondre',
        body: 'Les scénarios sans réponse et avec intervention sont comparés pour montrer quelles mesures, à quelle intensité, interrompent la transmission.',
      },
    ],

    briefTitle: 'Bulletin du jour',
    briefLead: 'Généré automatiquement chaque jour. Les jours calmes, il le dit.',
    briefCta: 'Consulter les bulletins précédents',
    briefEmpty: 'Le bulletin du jour n’a pas encore été généré.',
    briefError: 'Le bulletin n’a pas pu être chargé. Le système, lui, fonctionne toujours.',

    audienceTitle: 'À qui cela s’adresse',
    audienceLead: 'Un même signal doit prendre une forme différente selon qui le lit.',
    audiences: [
      {
        title: 'Réassurance et assurance',
        body: 'Indices d’exposition par pays et comparaison de portefeuille. Chaque réponse précise qu’il s’agit d’indices relatifs et non de probabilités absolues.',
        href: '/solutions/reinsurance',
      },
      {
        title: 'Gouvernements et santé publique',
        body: 'Traçage des voies d’importation et comparaison des interventions, avec l’effet modélisé de chaque mesure.',
        href: '/solutions/government',
      },
      {
        title: 'Organisations internationales et humanitaires',
        body: 'Signaux précoces dans les zones à surveillance faible — y compris des pays trop peu rentables pour que d’autres s’y intéressent.',
        href: '/solutions/ngo',
      },
    ],

    ctaTitle: 'Tout ce qu’il faut pour une évaluation est déjà ouvert',
    ctaBody:
      'Vous pouvez examiner l’ensemble du système sans réserver de démonstration. Pour un pilote ou un partenariat, contactez-nous via la page dédiée.',
    ctaButton: 'Nous contacter',
  },
};
