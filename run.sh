#!/bin/sh
# Zajistíme, že existuje složka pro DB v trvalém úložišti
mkdir -p /config/streamcinema/data

echo "Startuji StreamCinema API..."
# Spustíme uvicorn
# --app-dir /app říká, kde hledat main.py
python3 -m uvicorn main:app --host 0.0.0.0 --port 8765
