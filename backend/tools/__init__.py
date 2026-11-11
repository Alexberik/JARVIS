"""JARVIS tool registry."""
from __future__ import annotations
from typing import Any, Callable
from .weather import weather_tool
from .tasks import tasks_tool
from .system_info import time_tool, help_catalog

REGISTRY = {
    "weather": {"fn": weather_tool, "desc": "Погода (Open-Meteo)"},
    "tasks": {"fn": tasks_tool, "desc": "Задачи в Obsidian"},
    "time": {"fn": time_tool, "desc": "Дата и время"},
}

def list_tools():
    return [{"name": k, "desc": v["desc"]} for k, v in REGISTRY.items()]
