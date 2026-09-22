"""
SimpleAssisstant web UI — Expt 1 (Memory) + Expt 2 (Weather).

Run:
  py -3.12 web/app.py
Then open http://127.0.0.1:5000
"""

from __future__ import annotations

import asyncio

from flask import Flask, jsonify, render_template, request

from bridge import ask_memory, ask_weather

app = Flask(__name__)


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/memory")
def memory_page():
    return render_template("memory.html")


@app.get("/weather")
def weather_page():
    return render_template("weather.html")


@app.post("/api/memory")
def api_memory():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "Please enter a message."}), 400
    try:
        result = asyncio.run(ask_memory(query))
        return jsonify(result)
    except Exception as exc:  # noqa: BLE001 — show in UI for lab demos
        return jsonify({"error": str(exc)}), 500


@app.post("/api/weather")
def api_weather():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "Please enter a message."}), 400
    try:
        result = asyncio.run(ask_weather(query))
        return jsonify(result)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
