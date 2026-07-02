FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir mlflow

EXPOSE 5000

# Meme commande que le lancement local (README/CLAUDE.md), sans --backend-store-uri :
# stockage sur fichiers (./mlruns), monte en volume pour persister entre redemarrages.
CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]
