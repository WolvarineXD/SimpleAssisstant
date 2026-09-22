"""
Expt 2 — Data Dashboard Connector (MCP)

Tool:
  - get_current_weather(location) → fetches live data from wttr.in
"""

from __future__ import annotations

import json

import httpx
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("data-dashboard-weather")


@mcp.tool()
def get_current_weather(location: str) -> str:
    """Fetch current weather for a city or place using wttr.in.

    Args:
        location: City or place name, e.g. "Tokyo", "Bengaluru", "London".
    """
    place = location.strip()
    if not place:
        return "Please provide a location."

    url = f"https://wttr.in/{place}"
    params = {"format": "j1"}

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        return f"Weather API error for {place!r}: {exc}"
    except json.JSONDecodeError:
        return f"Could not parse weather data for {place!r}."

    try:
        current = data["current_condition"][0]
        nearest = data.get("nearest_area", [{}])[0]
        area = nearest.get("areaName", [{"value": place}])[0]["value"]
        country = nearest.get("country", [{"value": ""}])[0]["value"]

        temp_c = current.get("temp_C", "?")
        feels = current.get("FeelsLikeC", "?")
        humidity = current.get("humidity", "?")
        wind = current.get("windspeedKmph", "?")
        desc = current.get("weatherDesc", [{"value": "N/A"}])[0]["value"]

        return (
            f"Weather for {area}, {country}\n"
            f"  Condition : {desc}\n"
            f"  Temperature: {temp_c}°C (feels like {feels}°C)\n"
            f"  Humidity   : {humidity}%\n"
            f"  Wind       : {wind} km/h"
        )
    except (KeyError, IndexError, TypeError) as exc:
        return f"Unexpected weather payload for {place!r}: {exc}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
