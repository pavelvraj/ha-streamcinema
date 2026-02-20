FROM python:3.11-alpine

# Pracovní adresář uvnitř kontejneru
WORKDIR /app

# Instalace potřebných knihoven
RUN pip install --no-cache-dir fastapi uvicorn requests beautifulsoup4 lxml passlib python-multipart

# Zkopírujeme spouštěcí skript
COPY run.sh /run.sh
RUN chmod a+x /run.sh

# Zkopírujeme celou složku app (balíček app.*)
COPY app /app

# Spuštění aplikace
CMD ["/run.sh"]
