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
};
