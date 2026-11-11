"""Weather via Open-Meteo (no API key)."""
from __future__ import annotations
import json, urllib.parse, urllib.request
from typing import Any

def weather_tool(city: str = "Tbilisi", **kwargs) -> dict[str, Any]:
    city = (city or "Tbilisi").strip() or "Tbilisi"
    try:
        geo = _get("https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({"name": city, "count": 1, "language": "ru"}))
        results = geo.get("results") or []
        if not results:
            return {"ok": False, "reply": f"Город «{city}» не найден.", "tool": "weather"}
        place = results[0]
        lat, lon = place["latitude"], place["longitude"]
        name = place.get("name", city)
        country = place.get("country_code", "")
        w = _get("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({"latitude": lat, "longitude": lon, "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m", "timezone": "auto"}))
        cur = w.get("current") or {}
        desc = _code_to_text(cur.get("weather_code"))
        reply = f"Погода: {name} ({country})\n• {desc}\n• Температура: {cur.get('temperature_2m')}°C\n• Влажность: {cur.get('relative_humidity_2m')}%\n• Ветер: {cur.get('wind_speed_10m')} км/ч"
        return {"ok": True, "reply": reply, "tool": "weather", "data": cur}
    except Exception as e:
        return {"ok": False, "reply": f"Не удалось получить погоду: {e}", "tool": "weather"}

def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/0.2"})
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))

def _code_to_text(code) -> str:
    table = {0: "ясно", 1: "преимущественно ясно", 2: "переменная облачность", 3: "пасмурно", 45: "туман", 61: "дождь", 63: "умеренный дождь", 65: "сильный дождь", 71: "снег", 80: "ливень", 95: "гроза"}
    try:
        return table.get(int(code), f"код погоды {code}")
    except Exception:
        return "н/д"
