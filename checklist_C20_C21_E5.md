# Checklist d'audit — RNCP 37827 Développeur.se en IA
## Compétences C20 et C21 (épreuve E5)

> **Usage prévu** : ce fichier sert de grille d'audit pour Claude Code (ou tout autre agent) sur le dépôt `waterflow2`. Pour chaque critère, l'agent doit chercher une preuve concrète dans le code/dépôt (fichier, ligne, doc présente, incident réellement résolu et tracé...) avant de cocher. Ne jamais cocher une case sur la seule base d'une intention déclarée — il faut une preuve exécutable ou documentaire.
>
> Source : Grille d'évaluation individuelle RNCP 37827 (Simplon.co).

---

## E5 — Cas pratique (C20, C21)

Contexte de l'épreuve : à partir d'une application existante présentant **au moins une erreur technique**, en contexte réel ou fictif. Le cas pratique évalué a pour but la mise en place du monitorage applicatif et la résolution d'un incident technique dans l'application.

Livrable attendu :
- Documentation technique du monitorage.
- Documentation de la résolution de l'incident technique.

Évaluation :
- Correction de la documentation.
- Soutenance orale individuelle présentant le monitorage de l'application et la solution implémentée en réponse à l'incident technique traité.

---

### C20 — Surveiller une application IA (monitorage, journalisation, feedback loop MLOps)

> Attendu : mobiliser des techniques de monitorage et de journalisation, dans le respect des normes de gestion des données personnelles en vigueur, afin d'alimenter la feedback loop dans une approche MLOps, et de permettre la détection automatique d'incidents.

- [x] La documentation liste les métriques et les seuils et valeurs d'alerte pour chaque métrique à risque.
- [x] La documentation explicite les arguments en faveur des choix techniques pour l'outillage du monitorage de l'application.
- [x] Les outils (collecteurs, journalisation, agrégateurs, filtres, dashboard, etc.) sont installés et opérationnels à minima en environnement local.
- [x] Les règles de journalisation sont intégrées aux sources de l'application, en fonction des métriques à surveiller.
- [x] Les alertes sont configurées et en état de marche, en fonction des seuils préalablement définis.
- [x] La documentation couvre la procédure d'installation et de configuration des dépendances pour l'outillage du monitorage de l'application.
- [x] La documentation est communiquée dans un format qui respecte les recommandations d'accessibilité (par exemple celles de l'association Valentin Haüy ou de Microsoft).

### C21 — Résoudre les incidents techniques

> Attendu : apporter les modifications nécessaires au code de l'application et documenter les solutions pour en garantir le fonctionnement opérationnel.

- [ ] La ou les causes du problème sont identifiées correctement.
- [ ] Le problème est reproduit en environnement de développement.
- [ ] La procédure de débogage du code est documentée depuis l'outil de suivi.
- [ ] La solution documentée explicite chaque étape de la résolution et de son implémentation.
- [ ] La solution est versionnée dans le dépôt Git du projet d'application (par exemple avec une merge request).

---

## Instructions pour l'agent d'audit (Claude Code)

Pour chaque case ci-dessus :

1. **Chercher une preuve dans le dépôt** : configuration de monitorage/alerting, code de journalisation, doc dédiée, issue/ticket + PR de correction liés à un incident réel.
2. **Vérifier que la preuve fonctionne réellement**, pas seulement qu'elle existe :
   - Les alertes doivent être configurées avec des seuils explicites et un mécanisme de déclenchement vérifiable (pas juste un TODO ou un commentaire).
   - L'incident résolu doit être un vrai incident technique constatable (bug, comportement erroné, plantage), pas une amélioration ou une fonctionnalité manquante.
   - La procédure de débogage doit être tracée dans un outil de suivi (issue GitHub, ticket, etc.), avec un historique daté.
3. **Ne pas cocher une case sur la base d'une déclaration d'intention.**
4. Pour chaque case non cochée, indiquer précisément **quel fichier créer/modifier, ou quelle action effectuer** (ex. "provoquer volontairement un incident réel, le documenter, le corriger via une PR dédiée") pour la satisfaire.
5. Produire en sortie un tableau récapitulatif par compétence (C20, C21) avec le statut global : **Acquis / Non acquis / Partiellement acquis**, en listant les cases encore ouvertes.

### Point de vigilance spécifique à E5

Contrairement à E3/E4, cette épreuve exige un **incident technique réel et documenté de bout en bout** (cause → reproduction → débogage → correction → versionnement). Un monitorage qui tourne sans qu'aucun incident n'ait jamais été traité ne suffit pas à couvrir C21 : il faut soit un vrai bug déjà rencontré et corrigé sur le projet (vérifiable via l'historique Git/issues), soit en provoquer un volontairement pour la démonstration et documenter tout le processus.
