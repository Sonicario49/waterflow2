# Image Grafana pour le deploiement Render : le provisioning (datasource, alertes,
# dashboards) doit etre "cuit" dans l'image au build, faute de pouvoir monter un
# volume local comme le fait docker-compose.yml en developpement. La datasource
# Prometheus est ensuite ecrasee par la variante Render (URL publique HTTPS au lieu
# du nom DNS interne Docker Compose).
FROM grafana/grafana
COPY grafana/provisioning /etc/grafana/provisioning
COPY grafana/provisioning/datasources/prometheus.render.yml /etc/grafana/provisioning/datasources/prometheus.yml
