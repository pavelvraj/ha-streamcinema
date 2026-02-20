#!/bin/sh
echo "Startuji StreamCinema API..."
# Spouštíme modul app.main a v něm proměnnou app
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8765
