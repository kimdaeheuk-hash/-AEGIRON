import type { Dictionary } from '../types';

// 2026-11-22 개편 사전 — 헤임달(변이 추적) → 발할라 → 극지. 지운 페이지 사전은 커밋 83406e4 에 있음.
export const fr: Dictionary = {
  "nav": {
    "polar": "Veille polaire",
    "heimdall": "Heimdall",
    "valhalla": "Valhalla",
    "methodology": "Méthodologie",
    "government": "Entreprises et agences",
    "developers": "Développeurs · API",
    "security": "Sécurité",
    "about": "À propos",
    "contact": "Contact",
    "product": "Produit",
    "company": "Entreprise",
    "dashboard": "Vue opérationnelle",
    "openMenu": "Ouvrir le menu",
    "closeMenu": "Fermer le menu",
    "language": "Langue"
  },
  "footer": {
    "tagline": "Suivre le variant → juger la réponse.",
    "product": "Produit",
    "company": "Entreprise",
    "legal": "Mentions légales",
    "privacy": "Politique de confidentialité",
    "terms": "Conditions d’utilisation",
    "rights": "Tous droits réservés.",
    "location": "Busan, Corée du Sud",
    "disclaimer": "AEGIRON ne dispose pas encore d’un historique validé en matière de précision de détection précoce. Tous les chiffres de ce site mesurent l’échelle du système, et non sa performance prédictive."
  },
  "home": {
    "metaTitle": "AEGIRON — Suivi des variants · Couverture des contre-mesures",
    "metaDescription": "Consigne, chaque heure, le moment où la lignée dominante change dans les génomes publics de pathogènes (Heimdall), et évalue chaque jour si des vaccins et traitements existent face à cette menace (Valhalla). Pour les entreprises bio et du diagnostic et les agences nationales de biosécurité.",
    "eyebrow": "AEGIRON · Bio-santé",
    "title": "Suivre le variant,\npuis savoir si l'on peut riposter",
    "lead": "Nous consignons, chaque heure, le moment où la lignée dominante change dans les génomes publics de pathogènes (suivi des variants Heimdall), et évaluons chaque jour si des vaccins et traitements existent face à cette menace (Valhalla). Le criblage de séquences est en développement (validation en cours). Nos premiers clients : entreprises bio et du diagnostic, agences nationales de biosécurité.",
    "primaryCta": "Ouvrir la vue opérationnelle",
    "secondaryCta": "Pour entreprises et agences",
    "chainTitle": "Trois maillons",
    "chainLead": "Le suivi des variants (Heimdall) et la couverture des contre-mesures (Valhalla) passent devant ; la veille polaire reste un axe de recherche. Le criblage de séquences est signalé en développement jusqu'à la fin de sa validation. Seul ce qui fonctionne aujourd'hui est mentionné. Les changements d'état des trois maillons sont évalués et consignés chaque heure par BAIKAL MOB, le moteur de changements d'état.",
    "stages": [
      {
        "code": "HEIMDALL",
        "name": "Heimdall",
        "role": "Suivi des variants",
        "body": "Lorsque la lignée dominante d'un build génomique public (Nextstrain) change ou qu'une nouvelle lignée apparaît, l'instant est inscrit au registre. Un enregistrement, non un verdict.",
        "facts": [
          "Build public SARS-CoV-2 vérifié chaque heure · seuls les changements de lignée dominante et les nouvelles lignées sont consignés",
          "Lignées et proportions citées de Nextstrain · la transition est établie par notre registre en comparant au cycle précédent",
          "Criblage de séquences en développement (validation en cours) — faux positifs mesurés chaque semaine sur des séquences naturelles publiques · sensibilité non encore mesurée"
        ],
        "href": "heimdall",
        "linkLabel": "Ouvrir le registre des variants"
      },
      {
        "code": "VALHALLA",
        "name": "Valhalla",
        "role": "Juger la réponse",
        "body": "Pour chaque menace listée, consigne chaque jour une ligne indiquant si les contre-mesures enregistrées (stocks, produits autorisés) la couvrent et si les changements de lignée ébranlent ce verdict.",
        "facts": [
          "Verdict menace × stock × variant consigné chaque jour",
          "Fondé sur des données publiques (vaccins préqualifiés OMS, produits autorisés, registre des essais) · les niveaux de stock nationaux ne sont pas observés",
          "Enregistrez vos stocks pour calculer avec eux · sinon le résultat est signalé comme illustratif"
        ],
        "href": "valhalla",
        "linkLabel": "Ouvrir la section Valhalla"
      },
      {
        "code": "POLAR",
        "name": "Veille polaire",
        "role": "Détecter",
        "body": "Le pergélisol qui dégèle peut faire réapparaître des pathogènes longtemps enfouis, comme l’anthrax. Nous observons chaque heure la météo et la presse locale de 8 régions polaires.",
        "facts": [
          "8 régions (Yamal, Alaska, Arctique canadien, Groenland, Svalbard, péninsule Antarctique, etc.) observées chaque heure",
          "Température et jours de dégel = observations Open-Meteo · écart à la normale calculé sur une réanalyse de 16 ans",
          "Un niveau de veille, pas une alerte — les heures illisibles restent « non déterminé »"
        ],
        "href": "polar",
        "linkLabel": "Voir l’évolution polaire"
      }
    ],
    "healthTitle": "État de la collecte",
    "healthOk": "{ok}/{total} sources des trois couches saines (mesuré sur le serveur de production)",
    "healthUnknown": "État du serveur de production illisible (non déterminé)",
    "notTitle": "Ce que nous ne faisons pas",
    "notPoints": [
      "Alertes mondiales ou classements de risque par pays — retirés lors de la refonte de novembre 2026",
      "Prétendre à une précision de prévision ou de criblage — aucun historique validé pour l’instant",
      "Concevoir, synthétiser ou optimiser des séquences de pathogènes — défensif uniquement, jamais"
    ]
  },
  "polar": {
    "title": "Évolution polaire (enregistrée chaque heure)",
    "lead": "Première valeur enregistrée → valeur la plus récente par région · température (moyenne des maxima) et jours de dégel = observations météo ; Δ (par rapport à la moyenne décennale du même mois) = calcul · un enregistrement n’est ajouté que si la valeur change",
    "span": "Environ {days} jour(s) enregistré(s) — 30 jours pas encore atteints (enregistré depuis le 15/11/2026)",
    "undetermined": "{n} enregistrement(s) illisible(s) à leur heure exclu(s) de l’évolution (non déterminé)",
    "cols": {
      "region": "Région",
      "first": "Première valeur",
      "latest": "Plus récente",
      "change": "Variation",
      "records": "Enregistrements"
    },
    "empty": "Aucune valeur polaire enregistrée pour l’instant",
    "unavailable": "Historique polaire illisible (non déterminé)",
    "apiLabel": "API brute"
  },
  "variant": {
    "title": "Registre des variants (chaque heure)",
    "lead": "Dernière lignée dominante par build et transitions récentes · lignées, proportions et nombres de séquences cités de Nextstrain ; les transitions sont établies par notre registre en comparant au cycle précédent",
    "stateTitle": "État actuel",
    "transitionsTitle": "Transitions récentes (10 au plus)",
    "cols": {
      "build": "Build",
      "dominant": "Lignée dominante",
      "share": "Proportion",
      "sequences": "Séquences récentes",
      "observed": "Vérifié le",
      "kind": "Transition",
      "change": "Changement"
    },
    "transitions": {
      "first_seen": "Premier relevé",
      "dominant_changed": "Changement de dominante",
      "new_clade": "Nouvelle lignée",
      "none": "Aucun changement"
    },
    "empty": "Aucun relevé au registre pour l'instant",
    "noTransitions": "Aucune transition consignée",
    "unavailable": "Registre des variants illisible (non déterminé)",
    "screenerTitle": "Criblage de séquences — en développement (validation en cours)",
    "screenerNote": "Mesure du 2026-11-22 : sur 7 séquences naturelles publiques, 6,4 % de faux positifs par fragment de 1 000 bases et 1 sur 7 par séquence entière. La sensibilité (détection des séquences dangereuses) n'est pas encore mesurée — les résultats aident à prioriser, ce ne sont pas des verdicts.",
    "growthTitle": "Variants en progression (signal de croissance · estimation)",
    "growthLead": "Croissance hebdomadaire de la part de chaque lignée, en comparant les quatre dernières semaines aux quatre précédentes. Il vise à montrer les lignées qui progressent avant de devenir dominantes. C'est une estimation sensible à la taille des échantillons et aux délais de dépôt ; avec trop peu de séquences, elle n'est pas déterminée.",
    "growthCols": {
      "clade": "Lignée",
      "share": "Part (avant → récente)",
      "weekly": "Croissance hebdo.",
      "doubling": "Jours pour doubler la part",
      "count": "Séquences (avant → récentes)"
    },
    "growthNone": "Aucune lignée en progression",
    "growthUnavailable": "Signal de croissance illisible (non déterminé)"
  },
  "baikal": {
    "title": "BAIKAL MOB",
    "layer": "Moteur de changements d'état · au-dessus de l'ontologie",
    "lead": "Au-dessus de l'ontologie (les moteurs et leurs liens), BAIKAL évalue chaque heure l'état de chaque moteur et n'enregistre que les instants où un état change. Quatre états — normal, dégradé, arrêté, non déterminé — et ce qui n'a pas été observé n'est jamais compté comme normal. Lorsqu'un moteur amont s'arrête, il signale, en suivant les liens, quelles entrées en aval peuvent être périmées (sans modifier les états en aval).",
    "observedAt": "Dernière évaluation {t}",
    "stale": "Dernière évaluation il y a {m} min — la collecte s'est peut-être arrêtée. Ne lisez pas le tableau ci-dessous comme l'état actuel",
    "empty": "Aucune évaluation pour l'instant — la première apparaîtra après le prochain cycle de collecte (à l'heure pile)",
    "unavailable": "État BAIKAL illisible (non déterminé)",
    "cols": {
      "engine": "Moteur",
      "status": "État",
      "since": "Depuis",
      "reason": "Éléments",
      "observed": "Heure",
      "change": "Changement"
    },
    "statuses": {
      "ok": "🟢 Normal",
      "degraded": "🟡 Dégradé",
      "down": "🔴 Arrêté",
      "undetermined": "⚪ Non déterminé"
    },
    "observationStart": "Début d'observation",
    "impactsTitle": "Impact — là où une panne amont se propage",
    "noImpacts": "Aucune panne en propagation",
    "transitionsTitle": "Transitions d'état récentes",
    "noTransitions": "Aucune transition consignée",
    "apiLabel": "API brute"
  },
  "gap": {
    "title": "Carte des lacunes en contre-mesures",
    "lead": "Pour chaque pathogène du cadre de priorisation OMS 2024 (d'après la littérature secondaire), un tableau indique s'il existe un vaccin, un traitement, un produit approuvé par la FDA américaine, un diagnostic et une autorisation coréenne (MFDS). Les cases vides sont les besoins de préparation.",
    "summary": "{gap} pathogènes sur {total} présentent une lacune (ni vaccin, ni traitement, ni produit approuvé FDA, ou seulement en essais)",
    "noGap": "Aucun pathogène jugé en lacune (les lignes avec cases non déterminées ne sont pas comptées)",
    "unavailable": "Carte des lacunes illisible (non déterminée)",
    "cols": {
      "pathogen": "Pathogène",
      "vaccine": "Vaccin",
      "therapeutic": "Traitement",
      "fda": "Approuvé FDA",
      "diagnostic": "Diagnostic",
      "domestic": "Autorisation coréenne (MFDS)"
    },
    "statuses": {
      "approved": "🟢 Oui",
      "clinical": "🟡 Essais/limité",
      "none": "🔴 Aucun",
      "undetermined": "⚪ Non déterminé",
      "unsearchable": "— Non cherchable"
    },
    "gapMark": "Lacune",
    "legend": "🟢 approuvé/préqualifié · 🟡 en essais ou limité · 🔴 absent de ce registre · ⚪ non observé (non déterminé)",
    "caveat": "« Aucun » signifie absent de ce registre (préqualification OMS, ClinicalTrials.gov, openFDA, recherche par nom de produit MFDS), pas absent du monde. La liste des pathogènes n'a pas encore été vérifiée ligne par ligne avec les tableaux OMS 2024. La colonne coréenne est une recherche par nom de produit MFDS : elle ne distingue pas fabrication nationale et importation et manque les produits dont le nom omet la maladie. Sans clé MFDS, toutes les lignes sont non déterminées."
  },
  "pages": {
    "polar": {
      "metaTitle": "Veille polaire",
      "metaDescription": "Évolution enregistrée chaque heure de la température, des jours de dégel et de l’écart à la normale dans 8 régions polaires.",
      "eyebrow": "POLAR · Détecter",
      "title": "Veille polaire",
      "lead": "Anomalies météo des régions de pergélisol, observées et enregistrées chaque heure · niveau de veille, pas une alerte",
      "blocks": []
    },
    "about": {
      "metaTitle": "À propos",
      "metaDescription": "AEGIRON — une entreprise de bio-santé qui suit, heure par heure, l’évolution du génome d’un pathogène, et détermine si les moyens d’y faire face existent déjà.",
      "eyebrow": "ABOUT",
      "title": "AEGIRON",
      "lead": "Une entreprise technologique d’une seule personne, fondée à Busan. Nous suivons, heure par heure, l’évolution du génome d’un pathogène, et nous déterminons si les moyens de s’opposer à cette évolution existent déjà dans le monde. À ce seul dessein nous consacrons nos efforts. Les entreprises de biotechnologie et de diagnostic ainsi que les agences de biosécurité nationale sont nos premiers partenaires.",
      "blocks": [
        {
          "title": "Pourquoi nous nous consacrons à une seule chose",
          "body": "Jusqu’en novembre 2026, AEGIRON recueillait des signaux de maladies du monde entier. Mais plus notre portée s’élargissait, plus notre expertise s’amenuisait — et les évaluations extérieures le disaient sans détour. Nous avons donc choisi de renoncer à l’ambition dispersée. Nous avons placé le suivi des variants de pathogènes (Heimdall) au premier plan, laissé derrière elle le jugement de l’existence d’une réponse (Valhalla), et conservé la surveillance polaire comme recherche d’avenir. Nous croyons qu’une seule chose approfondie va plus loin que cent éparpillées."
        },
        {
          "title": "Les principes que nous tenons",
          "points": [
            "**Nous ne confondons jamais le mesuré, l’estimé et l’indirect.** Sur chaque écran, nous indiquons clairement quels chiffres viennent de l’observation et lesquels de l’interprétation.",
            "**Nous tenons trois états — succès, échec et non déterminé.** Ce que nous n’avons pas vu n’est jamais déguisé en zéro ni en « normal ».",
            "**Notre finalité est la défense.** Nous ne détenons aucune fonction qui conçoit, synthétise ou rend un pathogène plus dangereux."
          ]
        }
      ],
      "cta": {
        "title": "Nous accueillons l’adoption et le partenariat",
        "body": "Entreprises de biotechnologie et de diagnostic, institutions de recherche, et agences de biosécurité nationales et régionales — tous ceux qui souhaitent nous mettre à l’épreuve sont les bienvenus.",
        "label": "Nous contacter",
        "href": "contact"
      }
    },
    "methodology": {
      "metaTitle": "Méthodologie",
      "metaDescription": "Calcul du score de veille polaire, du registre des variants Heimdall et du verdict Valhalla, et leurs limites.",
      "eyebrow": "METHODOLOGY",
      "title": "Méthodologie",
      "lead": "Ce que chaque maillon mesure, et ce qu’il ne mesure pas",
      "blocks": [
        {
          "title": "Veille polaire",
          "kicker": "POLAR",
          "tone": "sky",
          "points": [
            "Température (moyenne des maxima) et jours de dégel = observations Open-Meteo",
            "Écart à la normale = **calcul** par rapport à la moyenne de réanalyse sur 16 ans du même mois",
            "Part des mots-clés de presse locale (ru/en/no) = **indicateur indirect** · pas une confirmation",
            "Le score de veille est un niveau, pas une alerte · les heures sans données météo sont « non déterminé »"
          ],
          "note": "Limites : chacune des 8 régions est un point représentatif unique · le lien causal dégel → exposition aux pathogènes reste une hypothèse"
        },
        {
          "title": "Heimdall",
          "kicker": "HEIMDALL",
          "tone": "violet",
          "points": [
            "Lit la lignée dominante et sa part sur 60 jours dans les builds publics Nextstrain",
            "Seuls les cycles où la lignée dominante change sont consignés · rien n’est écrit en l’absence de données",
            "Les indicateurs de criblage (CAI, CpG, entropie, anomalies locales) sont des **signaux de priorité**, pas des verdicts",
            "Le criblage est **en développement (validation en cours)** — sa spécificité (taux de faux positifs sur des séquences naturelles) est mesurée chaque semaine sur des séquences de référence publiques (GitHub Actions `heimdall-validation`). 2026-11-22 : 6,4 % par fragment de 1 000 bases, 1 sur 7 par séquence entière. La sensibilité et les verdicts ne sont pas mesurés."
          ],
          "note": "Limites : hérite des retards et biais de soumission des séquences publiques"
        },
        {
          "title": "Valhalla",
          "kicker": "VALHALLA",
          "tone": "forest",
          "points": [
            "Pour chaque menace, la couverture est jugée d’après les pathogènes cibles et l’efficacité déclarée des contre-mesures enregistrées",
            "Les signalements du registre des variants sont notés à côté du verdict",
            "Les niveaux de stock nationaux et l’efficacité par variant ne sont pas publics et ne sont pas observés"
          ],
          "note": "Limites : sans stocks enregistrés, le calcul utilise des données illustratives, et la réponse l’indique"
        }
      ]
    },
    "government": {
      "metaTitle": "Biosécurité nationale",
      "metaDescription": "Suivi des variants, verdict sur les contre-mesures et détection polaire pour les agences de biosécurité nationale.",
      "eyebrow": "GOVERNMENT",
      "title": "Pour les entreprises de biotech/diagnostic et les agences de biosécurité nationale",
      "lead": "Lire le génome du pathogène (Heimdall) et voir s’il existe une contre-mesure pour cette menace (Valhalla) dans une seule vue · les entreprises de biotechnologie et de diagnostic et les agences de biosécurité nationale sont les premiers clients",
      "blocks": [
        {
          "title": "Ce qu’obtient une agence",
          "items": [
            {
              "title": "Observation polaire précoce",
              "body": "Un relevé horaire des anomalies météo dans 8 régions de pergélisol",
              "meta": "Polar"
            },
            {
              "title": "Registre des transitions de lignée",
              "body": "Le registre des moments où la lignée dominante a changé dans les génomes publics",
              "meta": "Heimdall"
            },
            {
              "title": "Verdict sur les lacunes de contre-mesures",
              "body": "Une ligne par jour et par menace sur la couverture par les contre-mesures enregistrées",
              "meta": "Valhalla"
            }
          ]
        },
        {
          "title": "Modalités",
          "points": [
            "Examen immédiat via l’API publique",
            "Enregistrez le stock de l’agence pour calculer les verdicts avec lui (clé requise)",
            "Une configuration qui n’envoie jamais de données sensibles à des API externes est possible"
          ]
        },
        {
          "title": "Avertissement",
          "accent": true,
          "points": [
            "Aucun historique de précision de prévision",
            "Un niveau de veille n’est pas une alerte · les décisions de réponse restent à l’agence"
          ]
        }
      ],
      "cta": {
        "title": "Étude pilote",
        "body": "Documentation et démonstration pour les agences",
        "label": "Nous contacter",
        "href": "contact"
      }
    },
    "security": {
      "metaTitle": "Sécurité et gouvernance des données",
      "metaDescription": "Contrôle d’accès, contrôle des programmes à haut risque, confidentialité, souveraineté des données et gestion des secrets.",
      "eyebrow": "SECURITY & GOVERNANCE",
      "title": "Sécurité et gouvernance des données",
      "lead": "Qui peut modifier quoi, comment les fonctions sensibles sont contrôlées, où vont les données — publié tel qu’implémenté",
      "blocks": [
        {
          "title": "Contrôle d’accès",
          "kicker": "ACCESS CONTROL",
          "tone": "indigo",
          "specs": [
            {
              "label": "API au total",
              "value": "13 points d’accès"
            },
            {
              "label": "Authentification requise",
              "value": "5 — fonctions modifiant l’état, coûteuses ou à haut risque"
            },
            {
              "label": "Méthode",
              "value": "En-tête X-API-Key · plusieurs clés étiquetées · comparaison à temps constant"
            },
            {
              "label": "Sans clé configurée",
              "value": "Toutes les API d’écriture désactivées — jamais laissées ouvertes"
            }
          ]
        },
        {
          "title": "Contrôle des programmes à haut risque",
          "kicker": "HEIMDALL · VALHALLA",
          "tone": "violet",
          "points": [
            "Le criblage de séquences et l’enregistrement des stocks exigent une authentification · chaque appel est journalisé par étiquette de clé",
            "HEIMDALL est **réservé à la détection défensive** · aucune fonction de conception, de synthèse, d’optimisation ou de contournement"
          ]
        },
        {
          "title": "Principes de confidentialité",
          "kicker": "PRIVACY",
          "tone": "teal",
          "points": [
            "Données collectées : météo, génomes et marchés publics · aucune donnée individuelle de patient",
            "Le site et la vue opérationnelle fonctionnent sans connexion, publicité ni suivi des visiteurs"
          ]
        },
        {
          "title": "Secrets et intégrité opérationnelle",
          "kicker": "INTEGRITY",
          "tone": "sky",
          "items": [
            {
              "title": "Secrets",
              "body": "Clés API et identifiants uniquement dans les variables d’environnement de production · jamais dans le dépôt ni les documents"
            },
            {
              "title": "Barrière de déploiement",
              "body": "Seul le code qui passe les 365 tests automatisés atteint la production"
            },
            {
              "title": "Veille des défaillances silencieuses",
              "body": "Santé des sources consignée à chaque cycle · disponibilité vérifiée chaque heure de l’extérieur (GitHub Actions)"
            }
          ]
        }
      ],
      "cta": {
        "title": "Documentation pour audit de sécurité",
        "body": "Description de la configuration et des contrôles pour l’audit d’une agence",
        "label": "Nous contacter",
        "href": "contact"
      }
    },
    "developers": {
      "metaTitle": "Développeurs · API",
      "metaDescription": "API REST AEGIRON — 13 points d’accès, réponses JSON, authentification X-API-Key, documentation OpenAPI.",
      "eyebrow": "DEVELOPERS",
      "title": "Développeurs · API",
      "lead": "La source unique de chaque chiffre de la vue opérationnelle est l’API REST",
      "blocks": [
        {
          "title": "Bases",
          "kicker": "BASICS",
          "tone": "sky",
          "specs": [
            {
              "label": "URL de base",
              "value": "https://epiweather-api-production.up.railway.app"
            },
            {
              "label": "Format",
              "value": "REST · JSON"
            },
            {
              "label": "Authentification",
              "value": "Lecture publique · écriture/haut risque X-API-Key"
            },
            {
              "label": "Documentation interactive",
              "value": "/docs (OpenAPI)"
            }
          ]
        },
        {
          "title": "Points d’accès principaux",
          "kicker": "QUICK START",
          "tone": "teal",
          "items": [
            {
              "title": "Veille polaire",
              "body": "Score de veille, référence et tendance pour 8 régions",
              "meta": "GET /api/polar-watch"
            },
            {
              "title": "Historique polaire",
              "body": "Série d’observations enregistrée chaque heure",
              "meta": "GET /api/observations/history?layer=polar"
            },
            {
              "title": "Registre des variants",
              "body": "Transitions de lignée dominante dans les génomes publics",
              "meta": "GET /api/variant-ledger"
            },
            {
              "title": "Registre des verdicts",
              "body": "Verdicts quotidiens menace × stock × variant",
              "meta": "GET /api/valhalla/match-ledger"
            },
            {
              "title": "État opérationnel",
              "body": "Santé des sources, planificateur et instantanés de référence",
              "meta": "GET /api/status"
            }
          ]
        }
      ],
      "cta": {
        "title": "Clés d’intégration",
        "body": "Clés API par agence pour les fonctions d’écriture et à haut risque",
        "label": "Nous contacter",
        "href": "contact"
      }
    },
    "contact": {
      "metaTitle": "Contact",
      "metaDescription": "Comment joindre AEGIRON.",
      "eyebrow": "CONTACT",
      "title": "Contact",
      "lead": "Vous pouvez examiner l’ensemble du système sans réserver de démonstration. Si, après cet examen, vous avez des questions ou une proposition de collaboration, écrivez-nous ci-dessous.",
      "blocks": [
        {
          "title": "Coordonnées",
          "items": [
            {
              "title": "Courriel",
              "body": "kimdaeheuk@gmail.com",
              "meta": "La voie la plus rapide"
            },
            {
              "title": "Localisation",
              "body": "Busan, Corée du Sud",
              "meta": "KST (UTC+9)"
            }
          ]
        },
        {
          "title": "Particulièrement bienvenus",
          "points": [
            "**Corrections** — signalez-nous les erreurs de méthodologie ou de chiffres ; nous les vérifierons et en tiendrons compte.",
            "**Mise en relation avec des organisations de terrain** — un accès aux réseaux de surveillance réels est notre prochaine étape la plus importante.",
            "**Discussions de pilote** — réassureurs, gouvernements, organismes internationaux et organisations de terrain sont tous les bienvenus."
          ]
        }
      ]
    },
    "privacy": {
      "metaTitle": "Politique de confidentialité",
      "metaDescription": "Politique de confidentialité du site AEGIRON.",
      "eyebrow": "LEGAL",
      "title": "Politique de confidentialité",
      "lead": "Ce site n’exige aucune connexion de ses visiteurs et ne collecte aucune donnée personnelle.",
      "blocks": [
        {
          "title": "Ce que nous ne collectons pas",
          "points": [
            "Il n’y a ni inscription ni connexion : aucune information de compte n’est collectée.",
            "Ce site n’utilise aucun outil de suivi publicitaire ni de mesure d’audience.",
            "La consultation du tableau de bord ne requiert aucune information d’identification personnelle."
          ]
        },
        {
          "title": "Services externes",
          "body": "La vidéo de présentation de la page d’accueil est intégrée en mode de confidentialité renforcée de YouTube ; les règles de YouTube s’appliquent dès sa lecture. Les polices sont chargées depuis Google Fonts et jsDelivr, qui peuvent enregistrer des données d’accès telles que l’adresse IP."
        },
        {
          "title": "Lorsque vous nous écrivez",
          "body": "Si vous nous écrivez, le contenu et votre adresse ne servent qu’à vous répondre et ne sont jamais communiqués à des tiers."
        },
        {
          "title": "Modifications",
          "body": "Si cette politique change, cette page sera mise à jour."
        }
      ]
    },
    "terms": {
      "metaTitle": "Conditions d’utilisation",
      "metaDescription": "Conditions d’utilisation du site AEGIRON et de ses données publiques.",
      "eyebrow": "LEGAL",
      "title": "Conditions d’utilisation",
      "lead": "Les conditions qui s’appliquent lorsque vous utilisez ce site et le tableau de bord public.",
      "blocks": [
        {
          "title": "Nature des informations fournies",
          "accent": true,
          "points": [
            "Les informations de ce site sont fournies **à titre indicatif** et ne constituent pas un fondement de décision médicale, sanitaire ou d’investissement.",
            "Les chiffres de prévision et de scénario sont des **estimations sous hypothèses de modèle** — ni des mesures, ni des garanties.",
            "AEGIRON ne dispose pas encore d’un historique validé de précision en détection précoce.",
            "AEGIRON décline toute responsabilité quant aux conséquences de décisions fondées sur ces informations."
          ]
        },
        {
          "title": "Sources des données",
          "body": "Ce système collecte et traite des documents publics d’organismes tels que l’OMS et les CDC. Les droits d’auteur et conditions d’utilisation des documents d’origine restent ceux de chaque organisme. Les chiffres traités pouvant différer des originaux, consultez toujours les documents de l’organisme d’origine lorsqu’une citation officielle est nécessaire."
        },
        {
          "title": "Disponibilité",
          "body": "Le tableau de bord public peut être interrompu ou modifié sans préavis."
        }
      ]
    }
  },
  "api": {
    "tableTitle": "Tous les points d’accès",
    "tableLead": "Tous les points d’accès de l’API de production, regroupés par fonction. Le cadenas indique ceux qui exigent une X-API-Key.",
    "authYes": "Clé requise",
    "authNo": "Public",
    "tags": {
      "GAI": "Veille polaire",
      "후향 검증": "Heimdall · registre des variants",
      "Stage 0: 합성위협 탐지": "Heimdall · détection de menaces synthétiques et criblage",
      "Stage 8: 바이오방어": "Valhalla · verdicts de contre-mesures",
      "시스템": "Système · état opérationnel",
      "BAIKAL MOB": "BAIKAL MOB · moteur de changements d'état"
    }
  },
  "common": {
    "siteName": "AEGIRON"
  }
};
