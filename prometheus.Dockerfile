# Image Prometheus pour le deploiement Render : la config (cible de scrape) doit
# etre "cuite" dans l'image au build, faute de pouvoir monter un volume local comme
# le fait docker-compose.yml en developpement.
FROM prom/prometheus
COPY prometheus.render.yml /etc/prometheus/prometheus.yml
