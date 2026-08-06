import type { Dictionary } from '../types';

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
    methodology: 'Méthodologie',
    transparency: 'Ce que nous ignorons',
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
    metaTitle: 'AEGIRON — Alerte précoce des maladies infectieuses, telle qu’elle fonctionne',
    metaDescription:
      'Un système d’alerte précoce qui surveille 21 sources de données en temps réel. Le tableau de bord, la méthodologie complète et toutes les sources sont accessibles sans authentification — tout comme ce que nous n’avons pas encore validé.',

    heroEyebrow: 'Entièrement ouvert · Sans authentification',
    heroTitle: 'Voyez le système\ntel qu’il fonctionne aujourd’hui',
    heroLead:
      'La plupart des systèmes de veille épidémiologique se cachent derrière un rendez-vous commercial. AEGIRON publie le système en direct, la méthodologie, chaque source de données, et ce que nous n’avons pas encore validé. Regardez d’abord, jugez ensuite.',
    heroPrimaryCta: 'Ouvrir le tableau de bord',
    heroSecondaryCta: 'Voir le fonctionnement',
    heroNoLogin: 'Accès immédiat — sans inscription ni connexion',

    stats: [
      { value: '21', label: 'Sources en temps réel', note: 'OMS · CDC · presse en langue locale · climat · satellite' },
      { value: '106', label: 'Points d’accès API', note: 'Collecte · analyse · prévision · simulation' },
      { value: '217', label: 'Pays référencés', note: 'Indice de vulnérabilité fondé sur les données de la Banque mondiale' },
      { value: '740', label: 'Tests automatisés', note: 'Tous validés · relancés à chaque modification' },
    ],

    openTitle: 'Ce que nous publions',
    openLead:
      'L’échec le plus courant en surveillance épidémiologique n’est pas une prévision fausse, mais une prévision invérifiable. Nous publions donc tout ce qu’il faut pour vérifier les nôtres.',
    openItems: [
      {
        title: 'Le système en direct',
        body: 'Le tableau de bord que nous utilisons réellement. Pas une démonstration : le système opérationnel qui reçoit les signaux en ce moment.',
        href: '/dashboard',
        linkLabel: 'Ouvrir le tableau de bord',
      },
      {
        title: 'La méthodologie complète',
        body: 'Comment les signaux sont collectés, comment une anomalie est jugée, et comment les prévisions sont produites — exposé en quatre couches.',
        href: '/methodology',
        linkLabel: 'Lire la méthodologie',
      },
      {
        title: 'Toutes les sources',
        body: 'Les 21 sources listées sans exception, avec celles qui fonctionnent et celles qui sont actuellement bloquées.',
        href: '/data-sources',
        linkLabel: 'Voir les sources',
      },
      {
        title: 'Ce que nous ignorons',
        body: 'Points non validés, limites connues et lacunes de collecte non comblées. Vous ne trouverez pas cette page chez nos concurrents.',
        href: '/transparency',
        linkLabel: 'Lire les limites',
      },
    ],

    honestTitle: 'Ce qui n’a pas été validé',
    honestLead:
      'Peu d’entreprises placent cette section en page d’accueil. Mais si nous ne le disons pas en premier, la due diligence le dira à notre place.',
    honestPoints: [
      'Nous n’avons **aucun historique validé** de précision en détection précoce. C’est pourquoi aucune affirmation du type « détecté N jours plus tôt » ne figure sur ce site.',
      'Le système est pleinement opérationnel depuis 2026. Les résultats sur des épidémies antérieures sont des reconstitutions rétrospectives et n’équivalent pas à une performance en conditions réelles.',
      'Les chiffres issus des modules de prévision sont des **estimations sous hypothèses de modèle** — ni des mesures, ni des garanties.',
      'Notre collecte comporte des lacunes. Le système signale lui-même quels pays et quelles périodes sont manquants.',
    ],
    honestClose:
      'Voici ce que nous faisons à la place. Les sorties du modèle sont automatiquement comparées à la plus grande épidémie enregistrée ; lorsqu’un chiffre dépasse une plage défendable, le système **joint son propre avertissement** avant que la valeur ne quitte l’API. Lorsqu’une épidémie est manquée, nous distinguons « le modèle ne l’a pas détectée » de « nous n’avions aucune donnée pour la détecter ».',
    honestCta: 'Lire la liste complète des limites',

    pipelineTitle: 'Du signal à l’alerte',
    pipelineLead:
      'Cinq étapes. Ce que chaque étape écarte compte autant que ce qu’elle retient.',
    pipelineSteps: [
      {
        step: '01',
        title: 'Collecter',
        body: 'Rapports de situation de l’OMS, avis aux voyageurs des CDC, presse en langue locale dans 179 pays, climat, satellite et statistiques commerciales.',
      },
      {
        step: '02',
        title: 'Extraire',
        body: 'Maladie, pays, cas et décès sont structurés à partir des tableaux PDF et du texte des articles. Ce qui n’est pas reconnu est laissé vide plutôt que deviné.',
      },
      {
        step: '03',
        title: 'Juger',
        body: 'L’anomalie est mesurée par rapport au niveau habituel de chaque pays, et non à un seuil absolu — cinq signaux ne signifient pas la même chose partout.',
      },
      {
        step: '04',
        title: 'Prévoir',
        body: 'Des modèles de transmission estiment la propagation et le risque d’importation. Chaque valeur est accompagnée de ses hypothèses et de ses limites.',
      },
      {
        step: '05',
        title: 'Agir',
        body: 'Les scénarios sans intervention et avec intervention sont comparés, afin de répondre à « que faire », et pas seulement à « qu’est-ce qui arrive ».',
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

    ctaTitle: 'Regardez d’abord. Parlons ensuite.',
    ctaBody:
      'Vous pouvez consulter l’ensemble du système sans réserver de démonstration. Si des questions surgissent après, c’est le bon moment pour nous écrire.',
    ctaButton: 'Nous contacter',
  },
};
