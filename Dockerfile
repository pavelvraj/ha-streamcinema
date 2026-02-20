FROM python:3.11-alpine

# Instalace potřebných knihoven
RUN pip install --no-cache-dir fastapi uvicorn requests beautifulsoup4 lxml

# Pracovní adresář
WORKDIR /app

# Zkopírujeme spouštěcí skript
COPY run.sh /run.sh
RUN chmod a+x /run.sh

# Zkopírujeme aplikaci (tohle budeš pushovat přes git)
COPY app /app

CMD [ "/run.sh" ]
