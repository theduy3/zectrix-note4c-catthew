import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from hub.weather import TTL_SECONDS, Weather, WeatherError


NOW = datetime(2026, 11, 12, 10, 0, tzinfo=ZoneInfo("America/Vancouver"))


def payload(now):
    hourly_times = [(now + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(10)]
    daily_times = [(now + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    return {
        "current": {"temperature_2m": 6.4, "weathercode": 3, "wind_speed_10m": 9.2},
        "hourly": {"time": hourly_times,
                   "temperature_2m": [6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5],
                   "precipitation_probability": [12, 20, 55, 60, 70, 0, 0, 0, 0, 0],
                   "weathercode": [3, 3, 61, 61, 61, 2, 2, 1, 0, 0]},
        "daily": {"time": daily_times,
                  "weathercode": [61, 3, 3, 2, 95, 71, 0],
                  "temperature_2m_max": [9, 10, 11, 8, 7, 6, 12],
                  "temperature_2m_min": [2, 5, 4, 3, 1, 0, 4],
                  "precipitation_probability_max": [55, 10, 0, 0, 80, 30, 0]},
    }


class WeatherTests(unittest.TestCase):
    def test_snapshot_parses_current_hourly_and_daily(self):
        weather = Weather(fetch=lambda url: payload(NOW))
        snap = weather.snapshot(now=NOW)
        self.assertFalse(snap["stale"])
        current = snap["current"]
        self.assertEqual((current["temp_c"], current["condition"], current["label"], current["icon"]),
                         (6, "overcast", "Cloudy", "cloud"))
        self.assertEqual((current["high_c"], current["low_c"], current["precip_prob"], current["wind_kmh"]),
                         (9, 2, 55, 9))
        self.assertEqual(len(snap["hourly"]), 6)
        self.assertEqual(snap["hourly"][0]["label"], "Now")
        self.assertEqual(snap["hourly"][2]["icon"], "rain")
        self.assertEqual(len(snap["daily"]), 7)
        self.assertEqual(snap["daily"][0]["day"], "Today")
        self.assertEqual(snap["daily"][4]["icon"], "storm")
        self.assertEqual(snap["daily"][5]["icon"], "snow")

    def test_snapshot_caches_within_ttl_and_serves_stale_on_failure(self):
        calls = []
        ticking = [0.0]
        weather = Weather(fetch=lambda url: calls.append(url) or payload(NOW), clock=lambda: ticking[0])
        weather.snapshot(now=NOW)
        weather.snapshot(now=NOW)
        self.assertEqual(len(calls), 1)
        weather._fetch = lambda url: (_ for _ in ()).throw(OSError("offline"))
        ticking[0] += TTL_SECONDS + 1
        snap = weather.snapshot(now=NOW)
        self.assertTrue(snap["stale"])
        self.assertEqual(snap["current"]["temp_c"], 6)

    def test_snapshot_raises_without_any_cached_data(self):
        weather = Weather(fetch=lambda url: (_ for _ in ()).throw(OSError("offline")))
        with self.assertRaises(WeatherError):
            weather.snapshot(now=NOW)
        with self.assertRaises(WeatherError):
            weather.describe(now=NOW)

    def test_describe_summarizes_for_speech(self):
        weather = Weather(fetch=lambda url: payload(NOW))
        summary = weather.describe(now=NOW)
        self.assertIn("6 degrees", summary)
        self.assertIn("overcast", summary)
        self.assertIn("55% chance of precipitation", summary)
        self.assertIn("9 kilometers per hour", summary)

    def test_fetch_failure_beyond_stale_limit_raises(self):
        ticking = [0.0]
        weather = Weather(fetch=lambda url: payload(NOW), clock=lambda: ticking[0])
        weather.snapshot(now=NOW)
        weather._fetch = lambda url: (_ for _ in ()).throw(OSError("offline"))
        ticking[0] += 7 * 3600
        with self.assertRaises(WeatherError):
            weather.snapshot(now=NOW)


if __name__ == "__main__":
    unittest.main()
