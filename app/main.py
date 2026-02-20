from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def read_root():
    return {"Status": "StreamCinema API is running", "DB_Path": "/config/streamcinema/data"}

@app.get("/api/ping")
def ping():
    return "pong"
