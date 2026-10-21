"""Battman's engine log: a text file, one line per engine run.

Replaces Smiggles' shell commands (LogWriter / PruneLog / load-filtered-log):
- every `battman_engine_log` event the engine fires is appended to
  <config>/battman/engine.log as `<time>|<message>` (same line format as Smiggles'
  /config/smiggles/solar_debug.log);
- Sundays at 03:00 the file is cut to its last 4032 lines (two weeks of 5-minute runs),
  as Smiggles' PruneLog did;
- the Log page asks GET /api/battman/log?start=&end= for a time range. Until you
  migrate, that reads Smiggles' log file; after, Battman's.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

EVENT = "battman_engine_log"
KEEP_LINES = 4032
LOG_URL = "/api/battman/log"
BATTMAN_LOG = ("battman", "engine.log")
SMIGGLES_LOG = ("smiggles", "solar_debug.log")


def battman_path(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(*BATTMAN_LOG))


def smiggles_path(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(*SMIGGLES_LOG))


def line_for(when: str, message: str) -> str:
    """One log line: Smiggles' format (newlines in the message become spaces)."""
    return f"{when}|{message.replace(chr(10), ' ').replace(chr(13), ' ')}\n"


def append(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line)


def prune(path: Path, keep: int = KEEP_LINES) -> None:
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if len(lines) > keep:
        tmp = path.with_suffix(".tmp")
        tmp.write_text("".join(lines[-keep:]), encoding="utf-8")
        tmp.replace(path)


def _stamp(ts: str) -> str:
    """Smiggles' filter: 'T' -> space, drop everything from the first '.'."""
    ts = ts.replace("T", " ")
    return ts.split(".", 1)[0]


def read_range(path: Path, start: str, end: str) -> list[str]:
    """Lines whose time is within [start, end] ('YYYY-MM-DD HH:MM:SS', HA local time)."""
    if not path.exists():
        raise FileNotFoundError(str(path))
    out = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n")
            ts = _stamp(line.split("|", 1)[0])
            if start <= ts <= end:
                out.append(line)
    return out


def copy_in(src: Path, dst: Path) -> int:
    """Migrate: put Smiggles' log lines in front of Battman's. Returns lines copied."""
    if not src.exists():
        return 0
    old = src.read_text(encoding="utf-8", errors="replace")
    if old and not old.endswith("\n"):
        old += "\n"
    mine = dst.read_text(encoding="utf-8") if dst.exists() else ""
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(old + mine, encoding="utf-8")
    prune(dst)
    return old.count("\n")


@callback
def async_start(hass: HomeAssistant) -> callable:
    """Listen for engine log events and prune weekly. Returns an unsubscribe callable."""
    lock = asyncio.Lock()
    path = battman_path(hass)

    async def _on_log(event: Event) -> None:
        line = line_for(dt_util.now().isoformat(), str(event.data.get("message", "No message")))
        async with lock:
            try:
                await hass.async_add_executor_job(append, path, line)
            except OSError as err:
                _LOGGER.error("Battman couldn't write the engine log %s: %s", path, err)

    async def _prune(now) -> None:
        if now.weekday() != 6:  # Sunday
            return
        async with lock:
            await hass.async_add_executor_job(prune, path)

    unsubs = [
        hass.bus.async_listen(EVENT, _on_log),
        async_track_time_change(hass, _prune, hour=3, minute=0, second=0),
    ]

    def _stop() -> None:
        for u in unsubs:
            u()

    return _stop


class BattmanLogView(HomeAssistantView):
    """GET /api/battman/log?start=YYYY-MM-DD HH:MM:SS&end=...: the engine log for a range."""

    url = LOG_URL
    name = "api:battman:log"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        from .api import smiggles_in_charge  # noqa: PLC0415

        hass: HomeAssistant = request.app["hass"]
        start, end = request.query.get("start"), request.query.get("end")
        if not start or not end:
            return self.json({"message": "Log: start and end are needed"}, status_code=400)
        path = smiggles_path(hass) if smiggles_in_charge(hass) else battman_path(hass)
        try:
            lines = await hass.async_add_executor_job(read_range, path, start, end)
        except FileNotFoundError:
            return self.json({"message": f"No engine log yet ({path.relative_to(hass.config.config_dir)} not found)"},
                             status_code=404)
        return self.json({"file": str(path.relative_to(hass.config.config_dir)), "lines": lines})
