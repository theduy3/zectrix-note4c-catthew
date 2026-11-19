"""Render tasks and groceries on the VPS; replies are spoken by the Note4C."""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from hub.household import PACIFIC, event_elapsed

WIDTH, HEIGHT = 400, 300
BLACK, WHITE, YELLOW, RED = 0, 1, 2, 3
PALETTE = [0, 0, 0, 255, 255, 255, 245, 205, 20, 195, 30, 35]
FONTS = Path(__file__).resolve().parent.parent / "assets/fonts"


@lru_cache(maxsize=12)
def _font(size, bold=False):
    return ImageFont.truetype(str(FONTS / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size)


def _plain(text):
    text = unicodedata.normalize("NFC", str(text or ""))
    text = "".join(c for c in text if c == "\n" or not unicodedata.category(c).startswith("C"))
    text = re.sub(r"(?m)^#{1,6}\s+", "", text)
    return re.sub(r"\*\*(.*?)\*\*", r"\1", text)


def _lines(text, font, width):
    lines = []
    for paragraph in _plain(text).splitlines() or [""]:
        line = ""
        for word in paragraph.split():
            candidate = (line + " " + word).strip()
            if font.getlength(candidate) <= width:
                line = candidate
                continue
            if line:
                lines.append(line)
                line = ""
            while font.getlength(word) > width:
                end = 1
                while end < len(word) and font.getlength(word[:end + 1]) <= width:
                    end += 1
                lines.append(word[:end])
                word = word[end:]
            line = word
        lines.append(line)
    return lines


def _text(draw, x, y, text, *, size=16, bold=False, width=368, rows=1, color=BLACK):
    font = _font(size, bold)
    lines = _lines(text, font, width)
    if len(lines) > rows:
        lines = lines[:rows]
        last = lines[-1]
        while last and font.getlength(last + "…") > width:
            last = last[:-1]
        lines[-1] = last + "…"
    for index, line in enumerate(lines):
        draw.text((x, y + index * (size + 4)), line, font=font, fill=color, anchor="lt")


def _image():
    image = Image.new("P", (WIDTH, HEIGHT), WHITE)
    image.putpalette(PALETTE)
    return image


def _cloud_parts(cx, cy, w, h, grow=0.0):
    g = grow
    return [
        (cx - w * 0.36 - g, cy - h * 0.02 - g, cx + w * 0.36 + g, cy + h * 0.34 + g),
        (cx - w * 0.55 - g, cy + h * 0.04 - g, cx - w * 0.06 - g, cy + h * 0.44 + g),
        (cx + w * 0.04 - g, cy - h * 0.16 - g, cx + w * 0.52 + g, cy + h * 0.30 + g),
        (cx - w * 0.20 - g, cy - h * 0.30 - g, cx + w * 0.24 + g, cy + h * 0.14 + g),
    ]


def icon(draw, kind, cx, cy, size):
    """Draw a weather glyph in a square box centered at cx, cy."""
    s = size
    if kind == "moon":
        r = s * 0.36
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=YELLOW)
        draw.ellipse([cx - r * 0.55, cy - r * 0.75, cx + r * 1.05, cy + r * 0.45], fill=WHITE)
        draw.arc([cx - r, cy - r, cx + r, cy + r], start=250, end=500,
                 fill=BLACK, width=max(1, int(s * 0.05)))
    elif kind == "sun":
        r = s * 0.30
        for a in range(8):
            ang = a * math.pi / 4
            draw.line([(cx + math.cos(ang) * (r + 1.5), cy + math.sin(ang) * (r + 1.5)),
                       (cx + math.cos(ang) * (r + 4), cy + math.sin(ang) * (r + 4))],
                      fill=BLACK, width=max(1, int(s * 0.06)))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=YELLOW,
                     outline=BLACK, width=max(1, int(s * 0.07)))
    elif kind == "partly":
        sr = s * 0.20
        sx, sy = cx - s * 0.18, cy - s * 0.20
        draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=YELLOW, outline=BLACK, width=1)
        ccx, ccy, cw, ch = cx + s * 0.10, cy + s * 0.16, s * 0.78, s * 0.52
        for box in _cloud_parts(ccx, ccy, cw, ch, grow=1.2):
            draw.ellipse(box, fill=BLACK)
        for box in _cloud_parts(ccx, ccy, cw, ch):
            draw.ellipse(box, fill=WHITE)
    else:
        ccx, ccy, cw, ch = cx, cy - s * 0.06, s * 0.92, s * 0.60
        for box in _cloud_parts(ccx, ccy, cw, ch, grow=1.3):
            draw.ellipse(box, fill=BLACK)
        for box in _cloud_parts(ccx, ccy, cw, ch):
            draw.ellipse(box, fill=WHITE)
        bot = ccy + ch * 0.30
        if kind in ("rain", "drizzle"):
            count, length = (4, s * 0.11) if kind == "drizzle" else (3, s * 0.20)
            for i in range(count):
                dx = ccx - cw * 0.24 + i * (cw * 0.24)
                draw.line([(dx, bot + 1), (dx - s * 0.03, bot + length)],
                          fill=RED, width=max(1, int(s * 0.07)))
        elif kind == "snow":
            for i in range(3):
                dx, dy = ccx - cw * 0.24 + i * (cw * 0.24), bot + s * 0.10
                r = s * 0.05
                draw.ellipse([dx - r, dy - r, dx + r, dy + r], fill=BLACK)
        elif kind == "fog":
            for i in range(2):
                y = bot + s * (0.08 + i * 0.12)
                draw.line([(ccx - cw * 0.28, y), (ccx + cw * 0.28, y)],
                          fill=BLACK, width=max(1, int(s * 0.05)))
        elif kind == "storm":
            bx, by = ccx + cw * 0.05, bot + s * 0.02
            bolt = [(bx + s * 0.02, by), (bx - s * 0.07, by + s * 0.20),
                    (bx - s * 0.01, by + s * 0.20), (bx - s * 0.04, by + s * 0.36),
                    (bx + s * 0.08, by + s * 0.14), (bx + s * 0.01, by + s * 0.14)]
            draw.polygon(bolt, fill=YELLOW, outline=BLACK)


def _deg(value):
    return "--" if value is None else f"{value}\u00b0"


def pack_pixels(pixels):
    if len(pixels) % 4 or any(value > 3 for value in pixels):
        raise ValueError("pixels must be groups of four BWRY indices")
    return bytes((pixels[i] << 6) | (pixels[i + 1] << 4) | (pixels[i + 2] << 2) | pixels[i + 3]
                 for i in range(0, len(pixels), 4))


def pack_frame(image):
    if image.mode != "P" or image.size != (WIDTH, HEIGHT):
        raise ValueError("frame must be indexed 400x300")
    return pack_pixels(image.tobytes())


def unpack_frame(packed):
    if len(packed) != 30000:
        raise ValueError("frame must contain 30000 bytes")
    pixels = bytearray()
    for value in packed:
        pixels.extend((value >> 6, (value >> 4) & 3, (value >> 2) & 3, value & 3))
    image = Image.frombytes("P", (WIDTH, HEIGHT), bytes(pixels))
    image.putpalette(PALETTE)
    return image


@dataclass(frozen=True)
class Frame:
    pixels: bytes
    etag: str
    page: str
    next_page: str
    previous_page: str
    pages: int


def _due(task):
    try:
        value = task.get("due") or ""
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value)
        due = datetime.fromisoformat(value)
        return due.astimezone(PACIFIC).date() if due.tzinfo is not None else None
    except (ValueError, TypeError, OverflowError):
        return None


class Renderer:
    def __init__(self):
        _font(16)
        _font(24, True)

    def render(self, view, page, *, now):
        if page == "night":
            return self._night()
        pages = ("weather", "today", "groceries")
        selected = pages.index(page) if page in pages else 0
        key = pages[selected]
        image = _image()
        draw = ImageDraw.Draw(image)
        draw.fontmode = "1"
        titles = {"weather": "Weather", "today": "Tasks", "groceries": "Grocery Shopping"}
        _text(draw, 16, 12, titles[key], size=24, bold=True, width=270)
        _text(draw, 292, 17, now.strftime("%a, %b %-d"), size=12, width=94)
        draw.rectangle((16, 44, 383, 46), fill=YELLOW)
        if key == "weather":
            self._weather(draw, view.get("weather"))
        elif key == "today":
            tasks = [task for task in view.get("tasks", [])
                     if task.get("status") not in ("completed", "done", "cancelled")
                     and not task.get("grocery") and not event_elapsed(task, now)
                     and _due(task) == now.date()]
            tasks.sort(key=lambda task: task.get("title", ""))
            count = len(tasks)
            label = f"Showing 5 of {count} today's tasks" if count > 5 else f"Today · {count} tasks"
            _text(draw, 16, 57, label, size=12)
            for index, task in enumerate(tasks[:5]):
                self._task(draw, task, 77 + index * 34)
            if not tasks:
                _text(draw, 16, 90, "No tasks today.", size=20)
        elif key == "groceries":
            items = [item for item in view.get("groceries", []) if item.get("state") == "needed"]
            for index, item in enumerate(items[:7]):
                _text(draw, 16, 68 + index * 24, item.get("item"), size=18, width=368)
        if (view.get("request") or {}).get("status") in ("failed", "uncertain"):
            draw.rectangle((16, 249, 383, 269), fill=RED)
            warning = "Request unconfirmed · check before repeating"
            if view.get("stale"):
                warning = "Request unconfirmed · saved data · check records"
            _text(draw, 23, 252, warning, size=11, color=WHITE, width=354)
        elif view.get("reply_speech_status") == "failed":
            draw.rectangle((16, 249, 383, 269), fill=YELLOW)
            warning = ("Spoken reply unavailable · showing saved data" if view.get("stale")
                       else "Spoken reply unavailable · check current records")
            _text(draw, 23, 252, warning, size=11, width=354)
        elif view.get("stale"):
            draw.rectangle((16, 249, 383, 269), fill=YELLOW)
            _text(draw, 23, 252, "Some records unavailable · showing saved data", size=11, width=354)
        elif view.get("approval_pending"):
            _text(draw, 16, 252, "Calendar approval waiting in Telegram", size=12, color=RED)
        draw.line((16, 274, 383, 274), fill=BLACK)
        following, previous = pages[(selected + 1) % len(pages)], pages[(selected - 1) % len(pages)]
        label = {"weather": "weather", "today": "tasks", "groceries": "groceries"}[following]
        footer = f"Tap for {label} · {selected + 1}/{len(pages)}"
        if key == "groceries" and len(items) > 7:
            footer += f" · +{len(items) - 7} more"
        _text(draw, 16, 282, footer, size=11, width=285)
        # The device overlays its small OFFLINE badge in this reserved area.
        pixels = pack_frame(image)
        return Frame(pixels, hashlib.sha256(pixels).hexdigest(), key, following, previous, len(pages))

    @staticmethod
    def _weather(draw, weather):
        if not weather:
            _text(draw, 16, 90, "Weather unavailable.", size=20)
            return
        current, hourly, daily = weather["current"], weather["hourly"], weather["daily"]
        icon(draw, current["icon"], 40, 80, 48)
        _text(draw, 72, 54, _deg(current["temp_c"]), size=38, bold=True, width=110)
        _text(draw, 72, 96, current["label"], size=15, bold=True, width=180)
        _text(draw, 72, 114, f"H:{_deg(current['high_c'])} L:{_deg(current['low_c'])}",
              size=13, width=180)
        _text(draw, 258, 60, f"Precip {current['precip_prob']}%", size=13, width=125)
        wind = "--" if current["wind_kmh"] is None else str(current["wind_kmh"])
        _text(draw, 258, 80, f"Wind {wind} km/h", size=13, width=125)
        draw.line((16, 128, 383, 128), fill=BLACK)
        cw = (383 - 16) / 6
        for i, slot in enumerate(hourly[:6]):
            x = 16 + i * cw
            _text(draw, x, 134, slot["label"], size=9, bold=(i == 0), width=int(cw - 8))
            icon(draw, slot["icon"], x + cw / 2, 156, 20)
            _text(draw, x, 176, _deg(slot["temp_c"]), size=14, bold=True, width=int(cw - 8))
            prob = slot["precip_prob"]
            _text(draw, x, 194, f"{prob}%", size=8, width=int(cw - 8),
                  color=RED if prob >= 50 else BLACK)
        draw.line((16, 204, 383, 204), fill=BLACK)
        dw = (383 - 16) / 7
        for i, day in enumerate(daily[:7]):
            x = 16 + i * dw
            icon(draw, day["icon"], x + dw / 2, 213, 14)
            _text(draw, x, 224, day["day"], size=9, bold=(i == 0), width=int(dw - 6))
            _text(draw, x, 235, f"{_deg(day['high_c'])}/{_deg(day['low_c'])}",
                  size=10, bold=True, width=int(dw - 6))

    @staticmethod
    def _night():
        image = _image()
        draw = ImageDraw.Draw(image)
        draw.fontmode = "1"
        icon(draw, "moon", 200, 95, 60)
        _text(draw, 60, 150, "Press button", size=26, bold=True, width=280)
        _text(draw, 60, 185, "to talk to Catthew", size=22, width=280)
        _text(draw, 60, 230, "Good night", size=14, width=280)
        pixels = pack_frame(image)
        return Frame(pixels, hashlib.sha256(pixels).hexdigest(), "night", "weather", "weather", 3)

    @staticmethod
    def _task(draw, task, y):
        draw.rectangle((16, y + 3, 27, y + 14), outline=BLACK)
        _text(draw, 36, y, task.get("title") or "Family task", size=17, width=346)
