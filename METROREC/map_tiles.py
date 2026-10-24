import logging
import os
import sqlite3
import threading
import time
from _thread import LockType
from datetime import timezone
from email.utils import parsedate_to_datetime
from io import BytesIO
from pathlib import Path
from typing import Mapping, TypedDict
from urllib.parse import urlsplit

import requests
from PIL import Image, ImageTk
from tkintermapview import TkinterMapView


LOGGER = logging.getLogger(__name__)
USER_AGENT = "MetroREC/1.0 (+https://github.com/FabioJose08/Metrorec)"
MAX_TILE_REQUESTS = threading.BoundedSemaphore(2)
CACHE_PATH = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "MetroREC" / "map_tiles.sqlite3"
CACHE_LOCK = threading.RLock()
URL_LOCKS_LOCK = threading.Lock()
URL_LOCKS: dict[str, LockType] = {}
FAILED_TILES: dict[str, float] = {}
FAILED_TILES_LOCK = threading.Lock()
BLOCKED_SERVERS: dict[str, float] = {}
_cache_warning_reported = False
_cache_schema_ready = False


class CachedTile(TypedDict):
    body: bytes
    expires_at: float
    stale_until: float
    etag: str | None
    last_modified: str | None


def _url_lock(url: str) -> LockType:
    with URL_LOCKS_LOCK:
        return URL_LOCKS.setdefault(url, threading.Lock())


def _cache_connection() -> sqlite3.Connection:
    global _cache_schema_ready
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(CACHE_PATH, timeout=10)
    if not _cache_schema_ready:
        with CACHE_LOCK:
            if not _cache_schema_ready:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS tiles ("
                    "url TEXT PRIMARY KEY, body BLOB NOT NULL, expires_at REAL NOT NULL, "
                    "stale_until REAL NOT NULL, etag TEXT, last_modified TEXT)"
                )
                connection.commit()
                _cache_schema_ready = True
    return connection


def _read_cached_tile(url: str) -> CachedTile | None:
    connection = None
    with CACHE_LOCK:
        try:
            connection = _cache_connection()
            row = connection.execute(
                "SELECT body, expires_at, stale_until, etag, last_modified "
                "FROM tiles WHERE url = ?",
                (url,),
            ).fetchone()
        finally:
            if connection is not None:
                connection.close()
    if row is None:
        return None
    return {
        "body": row[0],
        "expires_at": row[1],
        "stale_until": row[2],
        "etag": row[3],
        "last_modified": row[4],
    }


def _cache_lifetime(headers: Mapping[str, str]) -> tuple[float, float, bool]:
    directives: dict[str, str | None] = {}
    for directive in headers.get("Cache-Control", "").split(","):
        name, separator, value = directive.strip().partition("=")
        directives[name.lower()] = value.strip().strip('"') if separator else None

    now = time.time()
    max_age_header = directives.get("max-age")
    if "no-cache" in directives:
        expires_at = now
    elif max_age_header is not None:
        try:
            age = max(0, int(headers.get("Age", "0")))
            max_age = int(max_age_header)
            expires_at = now + max(0, max_age - age)
        except (TypeError, ValueError):
            expires_at = now + 7 * 24 * 60 * 60
    elif "Expires" in headers:
        try:
            expires_at = parsedate_to_datetime(headers["Expires"]).timestamp()
        except (TypeError, ValueError, OverflowError):
            expires_at = now + 7 * 24 * 60 * 60
    else:
        expires_at = now + 7 * 24 * 60 * 60
    stale_if_error_header = directives.get("stale-if-error")
    try:
        stale_if_error = int(stale_if_error_header) if stale_if_error_header is not None else 0
    except ValueError:
        stale_if_error = 0
    return expires_at, expires_at + stale_if_error, "no-store" in directives


def _store_cached_tile(
    url: str,
    body: bytes,
    expires_at: float,
    stale_until: float,
    etag: str | None,
    last_modified: str | None,
) -> None:
    connection = None
    with CACHE_LOCK:
        try:
            connection = _cache_connection()
            connection.execute(
                "INSERT OR REPLACE INTO tiles "
                "(url, body, expires_at, stale_until, etag, last_modified) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (url, body, expires_at, stale_until, etag, last_modified),
            )
            connection.commit()
        finally:
            if connection is not None:
                connection.close()


def _delete_cached_tile(url: str) -> None:
    connection = None
    with CACHE_LOCK:
        try:
            connection = _cache_connection()
            connection.execute("DELETE FROM tiles WHERE url = ?", (url,))
            connection.commit()
        finally:
            if connection is not None:
                connection.close()


def _retry_delay(headers: Mapping[str, str], status_code: int) -> int:
    value = headers.get("Retry-After")
    if value:
        try:
            delay = int(value)
            if delay > 0:
                return delay
            if status_code != 403:
                return 1
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                delay = int(retry_at.timestamp() - time.time())
                if delay > 0:
                    return delay
                if status_code != 403:
                    return 1
            except (TypeError, ValueError, OverflowError):
                pass
    return 15 * 60 if status_code == 403 else 60


def _record_failure(url: str, delay: int) -> None:
    with FAILED_TILES_LOCK:
        FAILED_TILES[url] = time.monotonic() + delay


def _report_cache_failure(error: Exception) -> None:
    global _cache_warning_reported
    with FAILED_TILES_LOCK:
        if _cache_warning_reported:
            return
        _cache_warning_reported = True
    LOGGER.warning("Cache local de tiles indisponível; usando rede sem cache: %s", error)


def _tile_bytes(url: str) -> bytes | None:
    with _url_lock(url):
        now = time.time()
        cache_available = True
        try:
            cached = _read_cached_tile(url)
        except (OSError, sqlite3.Error) as error:
            _report_cache_failure(error)
            cached = None
            cache_available = False

        if cached and now < cached["expires_at"]:
            return cached["body"]

        host = urlsplit(url).netloc
        with FAILED_TILES_LOCK:
            if FAILED_TILES.get(url, 0) > time.monotonic():
                return cached["body"] if cached and now < cached["stale_until"] else None
            if BLOCKED_SERVERS.get(host, 0) > time.monotonic():
                return cached["body"] if cached and now < cached["stale_until"] else None

        headers = {"User-Agent": USER_AGENT}
        if cached and cached["etag"]:
            headers["If-None-Match"] = cached["etag"]
        if cached and cached["last_modified"]:
            headers["If-Modified-Since"] = cached["last_modified"]

        try:
            with MAX_TILE_REQUESTS:
                with requests.get(url, headers=headers, timeout=(5, 15)) as response:
                    if response.status_code == 304 and cached:
                        body = cached["body"]
                    else:
                        response.raise_for_status()
                        body = response.content
                        with Image.open(BytesIO(body)) as image:
                            image.verify()

                    expires_at, stale_until, no_store = _cache_lifetime(response.headers)
                    if cache_available:
                        try:
                            if no_store:
                                _delete_cached_tile(url)
                            else:
                                _store_cached_tile(
                                    url,
                                    body,
                                    expires_at,
                                    stale_until,
                                    response.headers.get("ETag") or (cached and cached["etag"]),
                                    response.headers.get("Last-Modified") or (cached and cached["last_modified"]),
                                )
                        except (OSError, sqlite3.Error) as error:
                            _report_cache_failure(error)
                    return body
        except requests.HTTPError as error:
            response = error.response
            status_code = response.status_code if response is not None else 0
            response_headers: Mapping[str, str] = response.headers if response is not None else {}
            delay = _retry_delay(response_headers, status_code)
            _record_failure(url, delay)
            log_failure = True
            if status_code in (403, 429) or status_code >= 500:
                with FAILED_TILES_LOCK:
                    log_failure = BLOCKED_SERVERS.get(host, 0) <= time.monotonic()
                    BLOCKED_SERVERS[host] = time.monotonic() + delay
            if log_failure:
                LOGGER.warning(
                    "Servidor de tiles %s respondeu HTTP %s; pausando novas solicitações por %s s.",
                    host,
                    status_code,
                    delay,
                )
            if cached and now < cached["stale_until"]:
                return cached["body"]
            return None
        except requests.RequestException as error:
            _record_failure(url, 60)
            with FAILED_TILES_LOCK:
                log_failure = BLOCKED_SERVERS.get(host, 0) <= time.monotonic()
                BLOCKED_SERVERS[host] = time.monotonic() + 60
            if log_failure:
                LOGGER.warning("Falha de rede ao acessar tiles em %s; pausando por 60 s: %s", host, error)
            if cached and now < cached["stale_until"]:
                return cached["body"]
            return None
        except OSError as error:
            _record_failure(url, 60)
            LOGGER.warning("Tile inválido recebido de %s: %s", url, error)
            if cached and now < cached["stale_until"]:
                return cached["body"]
            return None


class MetroRecMapView(TkinterMapView):
    tile_image_cache: dict[str, ImageTk.PhotoImage]

    def pre_cache(self) -> None:
        last_position = None
        while self.running:
            position: tuple[float, float] | None = self.pre_cache_position
            if position is None:
                time.sleep(0.1)
                continue

            if position != last_position:
                last_position = position
                zoom = round(self.zoom)
                center_x, center_y = round(position[0]), round(position[1])
                for x, y in (
                    (center_x - 1, center_y - 1),
                    (center_x, center_y - 1),
                    (center_x + 1, center_y - 1),
                    (center_x - 1, center_y),
                    (center_x + 1, center_y),
                    (center_x - 1, center_y + 1),
                    (center_x, center_y + 1),
                    (center_x + 1, center_y + 1),
                ):
                    if not self.running:
                        break
                    if f"{zoom}{x}{y}" not in self.tile_image_cache:
                        self.request_image(zoom, x, y)
            time.sleep(0.1)

    def request_image(
        self,
        zoom: int,
        x: int,
        y: int,
        db_cursor: sqlite3.Cursor | None = None,
    ) -> ImageTk.PhotoImage:
        key = f"{zoom}{x}{y}"
        if key in self.tile_image_cache:
            return self.tile_image_cache[key]

        url = self.tile_server.replace("{x}", str(x)).replace("{y}", str(y)).replace("{z}", str(zoom))
        if "tile.openstreetmap.org/" not in url:
            return super().request_image(zoom, x, y, db_cursor=db_cursor)

        body = _tile_bytes(url)
        if body is None:
            self.tile_image_cache[key] = self.empty_tile_image
            return self.empty_tile_image

        try:
            with Image.open(BytesIO(body)) as image:
                image.load()
                tile_image = ImageTk.PhotoImage(image)
        except OSError as error:
            _record_failure(url, 60)
            LOGGER.warning("Tile inválido recebido de %s: %s", url, error)
            self.tile_image_cache[key] = self.empty_tile_image
            return self.empty_tile_image

        if self.running:
            self.tile_image_cache[key] = tile_image
            return tile_image
        return self.empty_tile_image
