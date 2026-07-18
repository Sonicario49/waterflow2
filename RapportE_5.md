# Rapport professionnel : Bloc E5

**RNCP 37827, Développeur.se en Intelligence Artificielle**

| | |
|---|---|
| **Candidat·e** | Noureddine BENDANOUNE |
| **Date de session** | 31/07/2026 |
| **Thème du projet** | Waterflow 2 — prédiction de potabilité de l'eau (MLOps, XGBoost via MLflow) |
| **Dépôt Git** | https://github.com/Sonicario49/waterflow2 |

---

*Ce rapport présente les compétences C20 et C21 du bloc E5 ("Cas pratique — mise en place du
monitorage applicatif et résolution d'un incident technique"), dans l'ordre du REAC, chaque
compétence prise indépendamment. Chaque section reprend, en citation, les critères d'évaluation
exacts de la grille RNCP, puis une preuve concrète tirée du dépôt (fichier, ligne, commit, run
CI, capture). Le code n'est repris dans le corps du texte que lorsqu'il est indispensable à la
démonstration ; le reste est renvoyé en annexe, hors comptage.*

*Le travail décrit ici a été réalisé sur la branche `bug-e5`, mergée dans `main` via la pull
request #11. Les commandes citées (requêtes API Grafana, `curl`, `pytest`, statuts de run CI via
l'API GitHub) ont été exécutées réellement pendant la réalisation de ce cas pratique, pas
recopiées depuis une documentation antérieure.*

---

## 0. Contexte de l'épreuve E5

> **Cadre du cas pratique (grille RNCP) :** à partir d'une application existante présentant au
> moins une erreur technique, en contexte réel ou fictif. Le cas pratique évalué a pour but la
> mise en place du monitorage applicatif et la résolution d'un incident technique dans
> l'application.
>
> **Livrable** : documentation technique du monitorage + documentation de la résolution de
> l'incident technique.
> **Évaluation** : correction de la documentation + soutenance orale individuelle présentant le
> monitorage de l'application et la solution implémentée en réponse à l'incident traité.

Contrairement à C11 (monitorage du **modèle**, métriques F1/accuracy via MLflow, cf.
`RapportE_3.md`) et à C9/C13 (l'API elle-même), E5 porte sur le monitorage **système** de
l'application existante Waterflow 2 — est-ce que l'application tourne correctement (erreurs,
latence, dépendances externes) — et sur la résolution d'un incident technique introduit
délibérément dans ce même projet. Le professeur autorise explicitement à garder la même
thématique qu'E3/E4 plutôt que de repartir sur un projet vide ("il y a peu d'intérêt à faire du
monitoring/détection de bug dans un projet vide"), et recommande "d'introduire une erreur, que
vous corrigerez ensuite" plutôt que d'en chercher une survenue par accident. Choix fait ici :
l'incident (C21, section 2) a été sélectionné précisément parce qu'il est détectable par le
monitorage construit pour C20 (section 1) — une alerte réelle sur le taux d'erreurs serveur,
pas seulement des tests — pour que les deux compétences se referment l'une sur l'autre plutôt
que d'être traitées comme deux sujets séparés.

---

## 1. C20 : Surveiller une application IA (monitorage, journalisation)

> **Ce que le jury doit pouvoir cocher :**
> - La documentation liste les métriques et les seuils et valeurs d'alerte pour chaque métrique
>   à risque.
> - La documentation explicite les arguments en faveur des choix techniques pour l'outillage du
>   monitorage de l'application.
> - Les outils (collecteurs, journalisation, agrégateurs, filtres, dashboard, etc.) sont
>   installés et opérationnels à minima en environnement local.
> - Les règles de journalisation sont intégrées aux sources de l'application, en fonction des
>   métriques à surveiller.
> - Les alertes sont configurées et en état de marche, en fonction des seuils préalablement
>   définis.
> - La documentation couvre la procédure d'installation et de configuration des dépendances pour
>   l'outillage du monitorage de l'application.
> - La documentation est communiquée dans un format qui respecte les recommandations
>   d'accessibilité.

**Point de vigilance du professeur, à traiter explicitement** : ne pas confondre le monitorage du
**modèle** (C11, métriques F1/accuracy via MLflow, cf. `RapportE_3.md`) avec le monitorage du
**système** traité ici — et la mention d'une "feedback loop" dans l'intitulé du critère C20 de la
grille renvoie en réalité à une logique MLOps de réinjection vers le réentraînement (C11), pas au
sujet de cette section.

### 1.1 Architecture et outillage

```
FastAPI (Waterflow 2)          Prometheus              Grafana
   GET /metrics  ── scrape 15s ──►  :9090  ── évalue les règles d'alerte ──►  Alerting
                                                  │
                                                  └── query PromQL ──► Dashboards
```

5 services orchestrés par `docker-compose.yml` (`mlflow`, `api`, `streamlit`, `prometheus`,
`grafana`, cf. `RapportE_4.md` C15). Deux ajouts spécifiques à E5, provisionnés automatiquement
sans étape manuelle (`grafana/provisioning/`, monté en volume) :

- `datasources/prometheus.yml` — source de données Prometheus configurée au démarrage (avant,
  cette étape se faisait à la main dans l'UI à chaque nouvelle instance de Grafana).
- `dashboards/` (`dashboards.yml` + `json/waterflow2.json`) — dashboard "Waterflow 2 -
  Monitorage systeme (C20)" (uid `waterflow2-systeme`), 4 panels : taux de requêtes HTTP par
  statut, taux d'erreurs 5xx, latence p95, échecs OCR par cause — chacun correspondant
  directement à une des 3 alertes de la section 1.2.
- `alerting/rules.yml` — les 3 règles d'alerte elles-mêmes (détail section 1.2).

### 1.2 Métriques, seuils d'alerte et justification

| Métrique surveillée | Requête PromQL | Seuil d'alerte | Ce qu'un dépassement signifie |
|---|---|---|---|
| Taux d'erreurs serveur | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` | > 5% sur 5 min | Une dépendance (MLflow, OCR.space, la base) est probablement en panne |
| Latence API (p95) | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` | > 1 seconde sur 5 min | Ralentissement progressif détecté avant de devenir un incident complet |
| Échecs OCR | `sum(increase(ocr_failures_total[10m]))` | > 3 échecs sur 10 min | Distingue une panne du service externe OCR.space d'un fichier isolé illisible |

3 seuils volontairement peu nombreux ("pas besoin d'en avoir 50, juste quelques uns"), chacun
rattaché à une décision opérationnelle concrète. Règles versionnées et provisionnées
automatiquement (`grafana/provisioning/alerting/rules.yml`), pas configurées à la main dans
l'UI.

**Canal de notification, choix assumé** : les règles utilisent le contact point par défaut de
Grafana pour cet environnement de démonstration locale — aucune intégration Slack/email/SMS
réelle câblée, ce qui n'aurait aucune valeur de preuve sans un vrai destinataire à prévenir. En
production, le contact point serait un webhook Slack (astreinte) pour les alertes `critical`
(taux d'erreurs) et un email pour les alertes `warning` (latence, OCR) — le mécanisme de routage
de Grafana est le même, seule la destination change.

### 1.3 Journalisation liée aux métriques

`api/logging_config.py` fournit un logger structuré (JSON, un événement par ligne), utilisé dans
`api/` à la place de `print()`. Principe retenu : la métrique dit *qu'*un problème existe, le
log dit *pourquoi* — chaque log conservé répond à une question qu'une métrique seule ne peut pas
trancher.

| Log | Où | Métrique associée | Pourquoi on le garde |
|---|---|---|---|
| `model_loading` / `model_loaded` / `model_load_failed` | `api/main.py` (démarrage) | `GET /health` → `model_loaded` | Une alerte "taux d'erreurs élevé" causée par des `503` renvoie ici pour savoir si la cause est un MLflow injoignable au démarrage |
| `ocr_call_failed` (avec `reason`: `timeout`/`connection_error`/`http_error`/`processing_error`) | `api/ocr_router.py` | `ocr_failures_total` | L'alerte "Échecs OCR répétés" dit qu'il y a un problème ; le `reason` dit lequel, sans avoir à deviner |
| `audit_log_write_failed` | `api/main.py` (middleware `access_log`) | — (limite assumée, aucune métrique dédiée) | Les logs d'audit sont la seule trace de sécurité/RGPD de qui a fait quoi ; leur échec silencieux doit rester détectable |

### 1.4 Justification des choix d'outillage

**Prometheus + Grafana** plutôt qu'une stack ELK complète : le volume et la complexité réels de
ce projet ne justifient pas 3 conteneurs supplémentaires (Elasticsearch/Logstash/Kibana) et une
techno de recherche full-text que rien ici n'exploite, quand Prometheus suffit à modéliser des
métriques numériques dans le temps — cohérent avec la consigne "évitez les solutions clé en main
compliquées, faites au plus simple". La stack étant déjà en place pour C11, la réutiliser pour
C20 évite de maintenir deux outils de suivi différents pour un seul projet.

**Alerting intégré à Grafana** plutôt qu'un Alertmanager Prometheus séparé : un conteneur de
moins à opérer, configuration versionnée au même endroit que les dashboards, suffisant pour 3
règles — un Alertmanager séparé se justifierait pour un vrai besoin de routage complexe
(plusieurs équipes, escalade à paliers) que ce projet n'a pas.

**`import logging`** (bibliothèque standard) plutôt que Loki/ELK pour les logs : le niveau
minimal explicitement suffisant pour ce projet, logs structurés JSON lisibles en texte brut.

### 1.5 Preuve d'exécution réelle : le cycle complet Normal → Pending → Firing → Normal

C'est la preuve la plus forte de ce rapport : pas seulement "les alertes sont configurées et
s'évaluent sans erreur" (ce qui était déjà vérifié — `health: ok` sur les 3 règles via
`GET /api/prometheus/grafana/api/v1/rules`), mais un **déclenchement réel** obtenu en rejouant
l'incident C21 (section 2) contre la stack `docker-compose` en fonctionnement.

**Première tentative, échec instructif.** Le bug C21 (`IndexError` sur `/api/measurements`) a été
réintroduit temporairement dans l'image `api`, reconstruite et redéployée. 361 requêtes envoyées
sur ~200 secondes, toutes en `500` réel (confirmé : `curl` renvoie `Internal Server Error`,
statut `500`). Pourtant, `http_requests_total{endpoint="/api/measurements"}` restait **absent**
de Prometheus, et l'alerte "Taux d'erreurs serveur élevé" est restée `inactive` tout du long.

**Diagnostic** : `metrics_middleware` (`api/main.py`) incrémentait le compteur *après*
`await call_next(request)`. Une exception non gérée (`IndexError`, à la différence d'une
`HTTPException` volontaire comme `401`/`403`/`422`/`503`) remonte directement à travers le
middleware sans jamais produire de `response` à ce niveau — le code d'incrémentation ne
s'exécutait donc jamais. Les crashs bruts étaient invisibles pour Prometheus, contrairement aux
erreurs volontaires. Un vrai angle mort du monitorage, découvert en le testant réellement plutôt
qu'en supposant qu'il fonctionnait.

**Correction** : `try`/`finally` autour de `call_next`, avec `status_code = 500` par défaut avant
le `try` — la métrique s'enregistre désormais dans tous les cas (réponse normale, erreur
`HTTPException`, ou crash non géré), sans changer la réponse HTTP renvoyée au client. Vérifié :
`GET /metrics` affiche bien `http_requests_total{endpoint="/api/measurements",status="500"} 1.0`
après une seule requête cassée. Suite complète revalidée : 47/47.

**Deuxième tentative, succès.** Bug + fix de métriques tous deux en place, trafic soutenu
regénéré sur la route cassée. L'alerte "Taux d'erreurs serveur élevé" observée via l'API Grafana
passant par les 3 états attendus :

```
state=inactive health=ok   (x6, avant le seuil)
state=pending  health=ok   (x12, condition dépassée, "for: 2m" pas encore écoulé)
state=firing   health=ok   (seuil ET durée dépassés)
```

Capture prise à ce moment précis (`docs/Slidesupport/capture_grafana_taux_erreur.png`) : le
panel "Taux d'erreurs 5xx" du dashboard à ~100%, la règle en rouge dans l'onglet Alerting.

Le vrai correctif (`turbidity=f[8]`) a ensuite été redéployé (rebuild + restart du conteneur
`api`) : une requête de test renvoie de nouveau `201` avec une vraie prédiction, et l'alerte,
surveillée en continu via l'API Grafana, est revenue à `inactive` après que la fenêtre glissante
de 5 minutes se soit vidée des erreurs passées — cycle complet **Normal → Pending → Firing →
Normal** confirmé de bout en bout, pas seulement dans un sens.

`[Capture d'écran : docs/Slidesupport/capture_grafana_taux_erreur.png — alerte en Firing]`

### 1.6 Installation et configuration

```bash
docker compose up --build
```

Démarre les 5 services habituels. Les 3 fichiers de provisioning
(`grafana/provisioning/{datasources,alerting,dashboards}/`) sont montés automatiquement via
`docker-compose.yml` (`./grafana/provisioning:/etc/grafana/provisioning`) — aucune dépendance
supplémentaire, aucune étape manuelle dans l'UI au premier démarrage. Détail complet :
`docs/monitoring_systeme.md`, section 5.

### 1.7 Accessibilité

`docs/monitoring_systeme.md` est inclus dans la liste auditée de
`docs/ACCESSIBILITE_DOCUMENTATION.md` (10 fichiers au total) : hiérarchie de titres cohérente,
tableaux avec en-tête, aucune information portée uniquement par une couleur ou une image, format
Markdown texte brut cohérent avec le reste du projet.

---

## 2. C21 : Résoudre un incident technique

> **Ce que le jury doit pouvoir cocher :**
> - La ou les causes du problème sont identifiées correctement.
> - Le problème est reproduit en environnement de développement.
> - La procédure de débogage du code est documentée depuis l'outil de suivi.
> - La solution documentée explicite chaque étape de la résolution et de son implémentation.
> - La solution est versionnée dans le dépôt Git du projet d'application (par exemple avec une
>   merge request).

### 2.1 Choix du bug : pourquoi celui-ci plutôt qu'un des incidents déjà réels

3 incidents étaient déjà réellement survenus et documentés sur ce projet
(`tests/bugTrouvé_README.md`, incidents 1 à 3) : un problème d'invocation `pytest` en CI, un mock
MLflow instable selon l'ordre des fixtures, et une page RGPD manquante côté UI. Aucun ne
convenait pour C21 : les deux premiers sont des bugs de CI/tests, jamais détectables par un
monitorage système (Prometheus/Grafana ne voient jamais ces échecs) ; le troisième est une
fonctionnalité manquante, explicitement exclue par la grille RNCP ("pas une amélioration ou une
fonctionnalité manquante"). Un bug a donc été introduit délibérément, conformément à la consigne
du professeur ("partez d'une application existante et introduisez-y une erreur, que vous
corrigerez ensuite"), avec un critère de sélection supplémentaire : qu'il soit détectable par le
monitorage système construit pour C20, pas seulement par les tests — pour que la démonstration
ferme la boucle entre les deux compétences plutôt que de les traiter séparément.

### 2.2 Bug introduit, cause et reproduction

**Bug** : dans `api/main.py`, `add_measurement` stockait `turbidity=f[9]` au lieu de `f[8]`.
`FeaturesPayload` valide exactement 9 éléments (`min_length=9, max_length=9`), donc les indices
valides vont de 0 à 8 — `f[9]` est systématiquement hors limites. Commit du bug : `d122f7a`
(message explicite : "BUG (C21, introduit volontairement)").

**Cause identifiée** : erreur d'indexation d'une ligne (décalage d'un cran sur le dernier des 9
champs). Aucune requête valide ne peut échapper à ce crash — ce n'est pas un cas limite, c'est
systématique.

**Reproduit en environnement de développement** : exécution locale de `pytest`, échec immédiat
et systématique de 2 tests :

```
tests/test_pipeline.py::test_measurements_predict_potable PASSED -> FAILED
tests/test_pipeline.py::test_measurements_predict_non_potable PASSED -> FAILED

E       IndexError: list index out of range
api\main.py:283: IndexError
```

Reproduit également en CI, pas seulement en local : run GitHub Actions `29654803806`,
`conclusion=failure` (capture `docs/Slidesupport/ci_bug_rouge.png`).

### 2.3 Débogage et correction

**Correction** (branche `fix-measurements-indexerror`, commit `52e463d`) : `f[9]` → `f[8]`.

**Test de régression renforcé** : `test_get_measurements_history` ne vérifiait auparavant que le
champ `ph` de l'historique retourné. Il vérifie désormais que les 9 mesures sont persistées à la
bonne position, une par une :

```python
feature_order = [
    "ph", "hardness", "solids", "chloramines", "sulfate",
    "conductivity", "organic_carbon", "trihalomethanes", "turbidity",
]
for index, key in enumerate(feature_order):
    assert measures[key] == POTABLE_FEATURES[index], (
        f"Mesure '{key}' incorrecte : attendu {POTABLE_FEATURES[index]}, obtenu {measures[key]}"
    )
```

Ce test aurait détecté cette classe de bug quel que soit le champ mal indexé, pas seulement
l'occurrence précise sur `turbidity` — un test plus robuste que ce qui aurait suffi à faire
passer uniquement ce cas.

**Testé** : suite complète revalidée, 47/47 en local. **Déployé via CI** : run GitHub Actions
`29654856038`, `conclusion=success` (capture `docs/Slidesupport/ci_fix_vert.png`) — même chaîne
que le run rouge du bug, cette fois verte de bout en bout (validation des données, 47 tests,
réentraînement/validation du modèle, packaging des 3 images, publication sur `ghcr.io`).

### 2.4 Documentation et traçabilité (outil de suivi)

Documenté dans `tests/bugTrouvé_README.md`, "Incident 4", même format que les 3 incidents réels
précédents du projet (Contexte, Bug introduit, Reproduit, Diagnostic, Correction, Test renforcé)
— cohérence de style avec l'historique existant plutôt qu'un document isolé. Traçabilité assurée
par l'historique Git horodaté (commits `d122f7a`, `52e463d`, `25fd00a`, tous consultables avec
leur date et leur message complet) plutôt que par une issue GitHub dédiée — choix assumé : pour
un candidat seul, le commit horodaté + le document de suivi jouent le rôle d'"outil de suivi",
sans ticket séparé qui dupliquerait la même information.

### 2.5 Versionnement : branche et merge

Déroulé complet, chaque étape versionnée :

1. Bug introduit sur la branche `bug-e5` (commit `d122f7a`).
2. Branche dédiée `fix-measurements-indexerror` créée depuis ce commit.
3. Correction + test renforcé (`52e463d`), documentation de l'incident (`25fd00a`).
4. **Merge explicite** de `fix-measurements-indexerror` dans `bug-e5` avec `--no-ff` (commit
   `f29e997`, message : "Merge : correction de l'IndexError sur /api/measurements (C21)") — un
   vrai commit de merge, pas un rebase qui aurait effacé la trace de la branche.
5. Vérifié après coup, pas supposé : `git branch --merged bug-e5` liste bien
   `fix-measurements-indexerror`, et `git merge-base --is-ancestor fix-measurements-indexerror
   bug-e5` confirme que tous ses commits sont des ancêtres de `bug-e5`.
6. `bug-e5` mergée dans `main` via la pull request **#11** (commit de merge `75bdd58`).

`[Capture d'écran à insérer : graphe de branches/merge — git log --all --graph --oneline, ou
l'onglet "Network" du dépôt GitHub]`

---

## 3. Difficultés rencontrées et conclusion

**Deux tentatives ont été nécessaires pour obtenir un déclenchement réel de l'alerte (section
1.5).** La première a échoué silencieusement : 361 vraies requêtes en erreur envoyées, aucun
changement visible dans Prometheus ni dans l'état de l'alerte. Plutôt que de conclure trop vite
que le seuil était mal réglé, la métrique brute (`http_requests_total{endpoint=
"/api/measurements"}`) a été vérifiée directement — absente. Ça a mené au vrai diagnostic : le
middleware de métriques n'enregistrait rien pour les crashs non gérés, seulement pour les erreurs
HTTP volontaires. Corriger ce point avant de recommencer a transformé un échec de démo en une
découverte utile : un monitorage qui ne détecte que les erreurs "propres" (`HTTPException`) et
rate les crashs bruts a un vrai angle mort, précisément le genre de chose qu'un incident réel
révèle et qu'une configuration statique ne révèle jamais.

**Choisir le bon bug a demandé d'écarter les 3 incidents déjà réels du projet.** Le réflexe
initial était de réutiliser un incident déjà survenu plutôt que d'en fabriquer un — plus
"authentique" en apparence. Mais aucun des 3 (CI, mock de test, fonctionnalité manquante) ne
correspondait à ce que la grille attend pour C21 (un vrai bug applicatif, détectable par le
monitorage ou les tests). Introduire délibérément un bug, comme le suggère explicitement la
consigne du professeur, s'est révélé être le choix le plus rigoureux, pas un raccourci.

**Conclusion.** Le monitorage système de Waterflow 2 (C20) couvre 3 métriques à risque avec des
seuils justifiés, une journalisation reliée à ces métriques, un dashboard et des alertes
provisionnés automatiquement — et surtout, un déclenchement réel vérifié de bout en bout
(`Normal → Pending → Firing → Normal`), pas seulement une configuration qui s'évalue sans erreur.
L'incident C21 (IndexError sur `/api/measurements`) a été introduit, reproduit en local et en
CI, diagnostiqué, corrigé avec un test de régression plus robuste que nécessaire, documenté selon
le même format que les incidents réels du projet, et versionné via une branche de fix mergée
explicitement. Les deux compétences se referment l'une sur l'autre : c'est en rejouant
l'incident C21 contre le monitorage de C20 qu'un second bug, réel et jusque-là invisible, a été
trouvé et corrigé.

---

## Annexe : préparation de la soutenance orale

- **Repo Git accessible en amont** : https://github.com/Sonicario49/waterflow2
- **Démonstration prévue** : (1) montrer le dashboard Grafana "Waterflow 2 - Monitorage
  systeme (C20)" et l'onglet Alerting avec les 3 règles au vert, (2) montrer l'incident 4 dans
  `tests/bugTrouvé_README.md` et le test renforcé associé, (3) montrer le graphe de branches
  (`bug-e5` → `fix-measurements-indexerror` → merge) et les 2 runs CI (rouge puis vert), (4) si le
  temps le permet, rejouer en direct le déclenchement de l'alerte comme en section 1.5.
- **Minutage suggéré** (10 min visées pour E5) : 1-2 min contexte, ~4 min sur C20 (métriques,
  alertes, preuve de déclenchement réel), ~4 min sur C21 (bug, fix, branche, merge, CI), 1 min
  conclusion.

**Questions probables du jury et réponses préparées :**

**Q : Pourquoi avoir introduit un bug plutôt que d'utiliser un incident déjà réel sur le
projet ?**
Les 3 incidents déjà réels et documentés (`tests/bugTrouvé_README.md`, incidents 1-3) sont des
bugs de CI ou de tests, jamais détectables par un monitorage système, ou une fonctionnalité
manquante — explicitement exclue par la grille RNCP pour C21. Le professeur recommande
explicitement d'introduire une erreur pour cette épreuve ; le choix a été fait en plus de
sélectionner un bug qui referme la boucle avec le monitorage construit pour C20.

**Q : L'alerte s'est-elle vraiment déclenchée, ou seulement configurée ?**
Vraiment déclenchée — vérifié via l'API Grafana en interrogeant l'état de la règle en direct,
observé passant par `inactive` → `pending` → `firing` puis revenu à `inactive`, avec une capture
d'écran prise au moment du déclenchement. Ça a d'ailleurs révélé un vrai bug annexe (le
middleware de métriques n'enregistrait pas les crashs non gérés), corrigé au passage.

**Q : Pourquoi pas de vraie intégration Slack/email pour les alertes ?**
Choix assumé pour un environnement de démonstration locale : câbler une fausse intégration
n'aurait aucune valeur de preuve sans un vrai destinataire. Le mécanisme de routage de Grafana
(contact points, notification policies) est le même qu'en production ; seule la destination
changerait.

**Q : Le test renforcé (`test_get_measurements_history`) aurait-il suffi à détecter le bug
original ?**
Oui, et plus que ça : il vérifie les 9 mesures une par une, donc il aurait aussi détecté un
mauvais index sur n'importe lequel des 8 autres champs, pas seulement `turbidity` — plus robuste
que le minimum nécessaire pour faire passer ce cas précis.

---

## Annexe technique (hors comptage)

`[À COMPLÉTER si nécessaire pour la soutenance.]`
