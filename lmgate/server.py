"""aiohttp application: /auth, /stats, /healthz endpoints."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from aiohttp import web

from lmgate.allowlist import AllowList
from lmgate.auth import extract_key
from lmgate.stats import StatsWriter, build_stats_entry

log = logging.getLogger(__name__)


async def healthz(request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def auth(request: web.Request) -> web.Response:
    allowlist: AllowList = request.app["allowlist"]
    key = extract_key(dict(request.headers))
    if key is None:
        return web.Response(status=403, text="forbidden")
    entry = allowlist.get(key)
    if entry is None:
        return web.Response(status=403, text="forbidden")
    return web.Response(status=200, text="ok", headers={"X-LMGate-ID": entry.id})


async def stats(request: web.Request) -> web.Response:
    writer: StatsWriter = request.app["stats_writer"]
    try:
        payload = await request.json()
        entry = build_stats_entry(payload)
        writer.write(entry)
        writer.flush()
    except Exception:
        log.debug("Stats ingestion error", exc_info=True)
    return web.Response(status=200, text="ok")


async def _poll_allowlist(allowlist: AllowList, interval: int) -> None:
    """Periodically check allow-list file for changes and reload."""
    while True:
        await asyncio.sleep(interval)
        try:
            allowlist.reload_if_changed()
        except Exception:
            log.warning("Allow-list reload failed", exc_info=True)


def create_app(config: dict[str, Any]) -> web.Application:
    app = web.Application()
    app["config"] = config

    allowlist = AllowList(Path(config["auth"]["allowlist_path"]))
    allowlist.load()
    app["allowlist"] = allowlist

    stats_writer = StatsWriter(config["stats"]["output_path"])
    app["stats_writer"] = stats_writer

    async def on_startup(app: web.Application) -> None:
        interval = config["auth"]["poll_interval_seconds"]
        app["_allowlist_poll_task"] = asyncio.create_task(
            _poll_allowlist(app["allowlist"], interval)
        )

    async def on_cleanup(app: web.Application) -> None:
        app["_allowlist_poll_task"].cancel()
        try:
            await app["_allowlist_poll_task"]
        except asyncio.CancelledError:
            pass
        log.info("Shutting down: flushing stats writer")
        app["stats_writer"].close()

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    app.router.add_get("/auth", auth)
    app.router.add_post("/stats", stats)
    app.router.add_get("/healthz", healthz)
    return app
