# Monitorage système — Waterflow 2 (C20)

**Distinction avec C11, à ne pas confondre** : `docs/MONITORING_MODELE.md` (preuve pour C11)
documente le monitorage du **modèle** — ses métriques de performance (F1, accuracy) exposées via
MLflow et le Dashboard Qualité. Ce document-ci couvre le monitorage du **système** — est-ce que
l'application elle-même tourne correctement (disponibilité, erreurs, latence, dépendances
externes), indépendamment de la qualité des prédictions du modèle. Les deux répondent à des
questions différentes avec des outils différents (MLflow ici pour C11, Prometheus/Grafana pour
C20 — cf. `docs/MONITORING.md` pour le détail applicatif complémentaire). Précision utile : la
mention d'une "feedback loop" dans l'intitulé du critère C20 de la grille RNCP renvoie en réalité
à une logique de MLOps (réinjection de données vers le réentraînement du modèle, cf. C11), pas au
monitorage système traité ici.

## 1. Architecture

```
FastAPI (Waterflow 2)          Prometheus              Grafana
   GET /metrics  ── scrape 15s ──►  :9090  ── évalue les règles d'alerte ──►  Alerting
                                                  │
                                                  └── query PromQL ──► Dashboards
```

`prometheus-client` expose les métriques sur `GET /metrics` (`api/main.py`), Prometheus les
scrape toutes les 15 secondes (`prometheus.yml`), et Grafana les interroge à la fois pour les
dashboards et pour évaluer en continu 4 règles d'alerte (moteur d'alerting intégré à Grafana,
pas d'Alertmanager séparé — cf. justification en section 4).

## 2. Métriques surveillées, seuils d'alerte et canal de notification

| Métrique surveillée | Requête PromQL | Seuil d'alerte | Ce qu'un dépassement signifie |
|---|---|---|---|
| Taux d'erreurs serveur | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` | > 5% sur 5 min | Une dépendance (MLflow, OCR.space, la base) est probablement en panne — mieux vaut le savoir avant qu'un client ne s'en plaigne |
| Latence API (p95) | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` | > 1 seconde sur 5 min | Ralentissement progressif (fuite de ressource, dépendance lente) — détecté avant de devenir un incident complet |
| Échecs OCR | `sum(increase(ocr_failures_total[10m]))` | > 3 échecs sur 10 min | Distingue une vraie panne du service externe OCR.space d'un fichier isolé illisible envoyé par un client |
| Échecs d'écriture des logs d'audit | `sum(increase(audit_log_write_failures_total[10m]))` | > 0 sur 10 min | La traçabilité sécurité/RGPD n'est plus garantie — seuil à 0 car même une seule occurrence est significative (cf. section 3) |

Les 4 seuils sont volontairement peu nombreux (le projet n'en a pas besoin de 50) et rattachés
chacun à une décision opérationnelle concrète, pas choisis arbitrairement.

**Règles versionnées et provisionnées automatiquement**, pas configurées à la main dans l'UI :
`grafana/provisioning/alerting/rules.yml`, monté dans le conteneur Grafana via
`docker-compose.yml`. Vérifié en conditions réelles : après recréation du conteneur, les 4
règles apparaissent via l'API Grafana (`GET /api/v1/provisioning/alert-rules`) et s'évaluent
sans erreur contre Prometheus (`GET /api/prometheus/grafana/api/v1/rules` → `health: ok` sur les
4 règles, `state: inactive` en fonctionnement normal — aucune des 4 conditions n'est
actuellement dépassée).

**Déclenchement réel vérifié, pas seulement l'évaluation** : en rejouant l'incident 4
(`tests/bugTrouvé_README.md`, `IndexError` sur `/api/measurements`) contre la stack
`docker-compose` réelle et en générant du trafic soutenu sur la route cassée, l'alerte "Taux
d'erreurs serveur élevé" est passée par les 3 états attendus — `Normal` → `Pending` → `Firing` —
puis est revenue à `Normal` une fois le correctif redéployé. Cet essai a révélé un vrai angle
mort au passage : `metrics_middleware` n'incrémentait `http_requests_total` qu'*après*
`await call_next(request)`, donc jamais pour une exception non gérée (`IndexError`, par
opposition à `HTTPException`) qui remonte sans jamais produire de réponse à ce niveau — les
crashs bruts étaient invisibles pour Prometheus, contrairement aux erreurs volontaires
(`401`/`403`/`422`/`503`). Corrigé par un `try`/`finally` autour de `call_next` (`api/main.py`),
sans changer la réponse renvoyée au client — seulement l'observabilité du crash.

**Canal de notification** : les règles utilisent le contact point par défaut de Grafana pour cet
environnement local de démonstration — aucune intégration Slack/email/SMS réelle n'a été
câblée, ce qui n'aurait aucune valeur de preuve sans un vrai destinataire à prévenir. En
production, le contact point serait remplacé par un webhook Slack (canal d'astreinte) pour les
alertes `critical` (taux d'erreurs) et un email pour les alertes `warning` (latence, OCR) — le
mécanisme de routage (`notification policies` de Grafana) est le même, seule la destination
change.

## 3. Journalisation : quels logs, et pourquoi

`api/logging_config.py` fournit un logger structuré (JSON, un événement par ligne), utilisé dans
`api/` à la place de `print()`. Chaque log conservé correspond à une question qu'une métrique
seule ne peut pas répondre : la métrique dit *qu'*un problème existe, le log dit *pourquoi*.

| Log | Où | Métrique associée | Pourquoi on le garde |
|---|---|---|---|
| `model_loading` / `model_loaded` / `model_load_failed` | `api/main.py` (démarrage) | `GET /health` → `model_loaded` | Une alerte "taux d'erreurs élevé" causée par des `503` sur `/api/measurements` renvoie ici pour savoir si la cause est un MLflow injoignable au démarrage |
| `ocr_call_failed` (avec `reason`: `timeout`/`connection_error`/`http_error`/`processing_error`) | `api/ocr_router.py` | `ocr_failures_total` | L'alerte "Échecs OCR répétés" dit qu'il y a un problème ; le `reason` du log dit lequel (service injoignable ≠ fichier illisible envoyé par un client) sans avoir à deviner |
| `audit_log_write_failed` | `api/main.py` (middleware `access_log`) | `audit_log_write_failures_total` | Les logs d'audit (table `audit_logs`) sont la seule trace de sécurité/RGPD de qui a fait quoi ; l'alerte associée (cf. section 2) détecte tout échec d'écriture, même silencieux |

Les entrées de la table `audit_logs` elle-même (endpoint, méthode, statut, IP, utilisateur)
complètent ces logs applicatifs : ce sont des enregistrements structurés à but explicitement
sécurité/RGPD (cf. Rapport E3, C9), pas du logging opérationnel au sens strict.

## 4. Justification des choix d'outillage

**Prometheus + Grafana** plutôt qu'une stack ELK complète : le volume et la complexité réels de
ce projet ne justifient pas d'ajouter Elasticsearch/Logstash/Kibana (3 conteneurs
supplémentaires, une techno de recherche full-text que rien ici n'exploite) quand Prometheus
suffit à modéliser des métriques numériques dans le temps. Cohérent avec la consigne "évitez les
solutions clé en main compliquées, faites au plus simple". La stack Prometheus/Grafana étant déjà
présente dans le projet comme complément applicatif à C11 (cf. `docs/MONITORING.md`), la
réutiliser comme preuve principale de C20 évite de maintenir deux outils de suivi différents
pour un seul projet.

**Alerting intégré à Grafana** plutôt qu'un Alertmanager Prometheus séparé : un conteneur de
moins à opérer, configuration versionnée au même endroit que les dashboards, suffisant pour 4
règles. Un Alertmanager séparé se justifierait à partir d'un vrai besoin de routage complexe
(plusieurs équipes, escalade à paliers) que ce projet n'a pas.

**`import logging` (bibliothèque standard Python)** plutôt que Loki/ELK pour les logs : c'est le
niveau minimal explicitement suffisant pour ce projet — logs structurés JSON, lisibles en texte
brut, sans agrégateur de logs dédié à opérer en plus de Prometheus/Grafana.

## 5. Installation et configuration

```bash
docker compose up --build
```

Démarre les 5 services habituels (cf. `docs/MONITORING.md`). Deux ajouts, provisionnés
automatiquement sans étape manuelle :

- `grafana/provisioning/datasources/prometheus.yml` — configure la source de données Prometheus
  au démarrage (avant, cette étape se faisait à la main dans l'UI à chaque nouvelle instance de
  Grafana, cf. `docs/MONITORING.md`).
- `grafana/provisioning/alerting/rules.yml` — les 4 règles d'alerte de la section 2.

Ces deux fichiers sont montés dans le conteneur via `docker-compose.yml`
(`./grafana/provisioning:/etc/grafana/provisioning`). Aucune dépendance supplémentaire : les
images `prom/prometheus` et `grafana/grafana` sont les mêmes qu'avant, seule leur configuration
au démarrage change.

## 6. Accessibilité

Document Markdown texte brut, même convention que le reste du projet (cf.
`docs/ACCESSIBILITE_DOCUMENTATION.md`) : hiérarchie de titres cohérente, tableaux avec en-tête,
aucune information portée uniquement par une couleur ou une image.

## 7. Limite assumée

Le canal de notification réel (Slack/email/SMS) n'est pas câblé (cf. section 2) — un choix
délibéré pour un environnement de démonstration locale, pas un oubli. De même, la collecte de
feedback utilisateur qui remettrait en cause la pertinence du modèle (réinjection vers le
réentraînement) n'a pas été implémentée : c'est un axe explicitement optionnel pour ce projet,
qui relèverait de toute façon du monitorage du modèle (C11) plutôt que du monitorage système
documenté ici.
