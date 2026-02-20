#!/bin/sh
echo "Startuji StreamCinema API..."
python3 -m uvicorn main:app --host 0.0.0.0 --port 8765
