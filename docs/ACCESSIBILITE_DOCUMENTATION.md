# Accessibilité du format de la documentation — Waterflow 2

Ce document couvre l'accessibilité du **format** des livrables documentaires du projet
(`README.md`, `CLAUDE.md`, `tests/test_README.md`, `tests/bugTrouvé_README.md`,
`notebooks/user_stories.md`, `notebooks/parcours_utilisateurs.md`), et sert de preuve pour les
critères d'audit associés (C9, C11, C12, C13, C17, C18, C19). Pour l'accessibilité de
l'**application** elle-même (UI Streamlit), voir les critères WCAG intégrés dans
`notebooks/user_stories.md`.

Référentiels suivis : recommandations de l'association [Valentin Haüy](https://www.avh.asso.fr/)
pour la production de documents numériques accessibles, et WCAG 2.1 (même référentiel que les
user stories du projet).

## Choix de format

Toute la documentation est écrite en **Markdown texte brut**, versionné avec le code. Ce choix
est délibéré du point de vue accessibilité : contrairement à un PDF scanné ou une capture d'écran,
un fichier Markdown est nativement lisible par un lecteur d'écran (texte brut) et, une fois rendu
par GitHub/VSCode, produit du **HTML sémantique** (vrais titres, vraies listes, vrais blocs de
code) plutôt qu'une mise en forme purement visuelle.

## Points vérifiés

- **Hiérarchie des titres respectée, sans saut de niveau** (toujours H1 → H2 → H3) : vérifié sur
  les 6 fichiers ci-dessus. Une hiérarchie cohérente permet une navigation par titres au clavier
  ou au lecteur d'écran (ex. touche `H` sous NVDA/JAWS).
- **Aucune information transmise uniquement par une image ou une couleur** : la documentation ne
  contient aucune image sans texte équivalent. Les diagrammes de parcours utilisateurs
  (`notebooks/parcours_utilisateurs.md`) sont écrits en Mermaid, donc **du texte brut lisible tel
  quel** par un lecteur d'écran (`flowchart TD`, nœuds et flèches nommés explicitement) ; le rendu
  graphique via [mermaid.live](https://mermaid.live) est une restitution optionnelle, pas le seul
  moyen d'accéder à l'information.
- **Liens avec un intitulé explicite** : aucun lien du type "cliquez ici" ou URL nue sans contexte
  (ex. `[mermaid.live](https://mermaid.live)`, jamais un lien qui ne se comprend pas hors contexte).
- **Pas de tableau sans en-tête** : aucun tableau Markdown mal formé dans la documentation actuelle.
- **Langage clair, sections courtes** : chaque document est découpé en sections numérotées ou
  thématiques plutôt qu'en un bloc de texte continu, pour faciliter le survol au lecteur d'écran.

## Limite assumée

Cette vérification porte sur la **structure** du format (titres, liens, alternatives textuelles),
pas sur un contrôle outillé complet (contraste, navigation clavier de bout en bout) — comme précisé
dans `notebooks/user_stories.md`, aucun audit accessibilité outillé n'a été mené sur le rendu final
dans un lecteur d'écran réel.
