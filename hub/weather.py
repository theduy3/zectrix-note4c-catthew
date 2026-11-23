"""Vancouver weather from Open-Meteo: cached ~30 minutes, safe to serve stale."""
from __future__ import annotations

import json
import threading
import time
import urllib.request
from datetime import datetime

from hub.household import PACIFIC

URL = ("https://api.open-meteo.com/v1/forecast"
       "?latitude=49.2827&longitude=-123.1207"
       "&current=temperature_2m,weathercode,wind_speed_10m"
       "&hourly=temperature_2m,precipitation_probability,weathercode"
       "&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
       "&timezone=America%2FVancouver&forecast_days=7")
TTL_SECONDS = 30 * 60
MAX_STALE_SECONDS = 6 * 3600
TIMEOUT_SECONDS = 10
MAX_BYTES = 1024 * 1024

# WMO weather interpretation codes -> (spoken condition, display label, icon)
_CONDITIONS = {
    0: ("clear sky", "Clear", "sun"),
    1: ("mainly clear", "Clear", "sun"),
    2: ("partly cloudy", "Partly", "partly"),
    3: ("overcast", "Cloudy", "cloud"),
    45: ("fog", "Fog", "fog"),
    48: ("depositing rime fog", "Fog", "fog"),
    51: ("light drizzle", "Drizzle", "drizzle"),
    53: ("drizzle", "Drizzle", "drizzle"),
    55: ("heavy drizzle", "Drizzle", "drizzle"),
    56: ("freezing drizzle", "Frz drizzle", "drizzle"),
    57: ("freezing drizzle", "Frz drizzle", "drizzle"),
    61: ("slight rain", "Rain", "rain"),
    63: ("rain", "Rain", "rain"),
    65: ("heavy rain", "Rain", "rain"),
    66: ("freezing rain", "Frz rain", "rain"),
    67: ("freezing rain", "Frz rain", "rain"),
    71: ("slight snow", "Snow", "snow"),
    73: ("snow", "Snow", "snow"),
    75: ("heavy snow", "Snow", "snow"),
    77: ("snow grains", "Snow", "snow"),
    80: ("slight rain showers", "Rain", "rain"),
    81: ("rain showers", "Rain", "rain"),
    82: ("heavy rain showers", "Rain", "rain"),
    85: ("slight snow showers", "Snow", "snow"),
    86: ("snow showers", "Snow", "snow"),
    95: ("a thunderstorm", "Storm", "storm"),
    96: ("a thunderstorm with hail", "Storm", "storm"),
    99: ("a thunderstorm with hail", "Storm", "storm"),
}


def _condition(code):
    return _CONDITIONS.get(code, ("cloudy", "Cloudy", "cloud"))


class WeatherError(RuntimeError):
    pass


def _round(value):
    return None if value is None else round(value)


class Weather:
    """Fetches and caches the Vancouver forecast; returns render/voice snapshots."""

    def __init__(self, fetch=None, clock=time.monotonic):
        self._fetch = fetch or self._http
        self._clock = clock
        self._lock = threading.Lock()
        self._cache = None
        self._fetched = None

    @staticmethod
    def _http(url):
        request = urllib.request.Request(url, headers={"User-Agent": "catthew-note4c/1.0"})
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("weather response exceeds 1 MiB")
        return json.loads(raw)

    def snapshot(self, *, now=None):
        """Return the parsed forecast; cached under TTL, stale up to 6h on fetch failure."""
        now = now or datetime.now(PACIFIC)
        with self._lock:
            fresh = (self._cache is not None and self._fetched is not None
                     and self._clock() - self._fetched < TTL_SECONDS)
            if fresh:
                return self._cache
        try:
            parsed = self._parse(self._fetch(URL), now)
        except Exception:
            with self._lock:
                if (self._cache is not None and self._fetched is not None
                        and self._clock() - self._fetched < MAX_STALE_SECONDS):
                    stale = dict(self._cache)
                    stale["stale"] = True
                    return stale
            raise WeatherError("weather unavailable") from None
        with self._lock:
            self._cache, self._fetched = parsed, self._clock()
        return parsed

    def describe(self, *, now=None):
        """Spoken summary for the voice channel."""
        snap = self.snapshot(now=now)
        current = snap["current"]
        parts = [f"It is {current['temp_c']:.0f} degrees with {current['condition']}",
                 f"high {current['high_c']:.0f}, low {current['low_c']:.0f}"]
        if current["precip_prob"]:
            parts.append(f"{current['precip_prob']}% chance of precipitation")
        if current["wind_kmh"]:
            parts.append(f"wind {current['wind_kmh']:.0f} kilometers per hour")
        if snap.get("stale"):
            parts.append("from the last saved forecast")
        return ", ".join(parts) + "."

    def _parse(self, data, now):
        current = data["current"]
        hourly, daily = data["hourly"], data["daily"]
        times = hourly["time"]
        start = next((i for i, t in enumerate(times) if t[:13] == now.strftime("%Y-%m-%dT%H")), 0)
        slots = []
        for i in range(start, min(start + 6, len(times))):
            moment = datetime.fromisoformat(times[i])
            code = hourly["weathercode"][i]
            slots.append({
                "label": "Now" if i == start else moment.strftime("%-I%p"),
                "code": code, "condition": _condition(code)[1], "icon": _condition(code)[2],
                "temp_c": _round(hourly["temperature_2m"][i]),
                "precip_prob": int(hourly["precipitation_probability"][i] or 0)})
        days = []
        for i in range(min(7, len(daily["time"]))):
            moment = datetime.fromisoformat(daily["time"][i])
            code = daily["weathercode"][i]
            days.append({
                "day": "Today" if i == 0 else moment.strftime("%a"),
                "code": code, "condition": _condition(code)[1], "icon": _condition(code)[2],
                "high_c": _round(daily["temperature_2m_max"][i]),
                "low_c": _round(daily["temperature_2m_min"][i]),
                "precip_prob": int(daily["precipitation_probability_max"][i] or 0)})
        today = days[0] if days else {}
        code = current["weathercode"]
        return {
            "stale": False,
            "generated_at": now.isoformat(timespec="seconds"),
            "current": {
                "temp_c": _round(current["temperature_2m"]),
                "code": code, "condition": _condition(code)[0],
                "label": _condition(code)[1], "icon": _condition(code)[2],
                "high_c": today.get("high_c"), "low_c": today.get("low_c"),
                "precip_prob": today.get("precip_prob", 0),
                "wind_kmh": _round(current["wind_speed_10m"])},
            "hourly": slots,
            "daily": days,
        }
