"""Library code for geolocation"""
from os import replace as file_replace
from asyncio import to_thread
from geoip2.database import Reader
from geoip2.models import City
from geoip2.errors import AddressNotFoundError
from pathlib import Path
from asyncio import sleep
from github import Github
from datetime import datetime, UTC
from zoneinfo import ZoneInfo
from threading import Lock
from logging import getLogger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.job import Job

_logger = getLogger(__name__)
_db = Path(__file__).parent / "GeoLite2-City.mmdb"
_db_tmp = _db.parent / "GeoLite2-City.mmdb.tmp"
_db_id = _db.parent / "GeoLite2-City.hash"
_reader = None
_lock = Lock()
_scheduler = AsyncIOScheduler()
_github_repo = None

def lookup_city(ip: str) -> City | None:
    global _reader
    with _lock:
        if _reader is None:
            if not _db.exists():
                return None
            _reader = Reader(str(_db))
        try:
            return _reader.city(ip)
        except AddressNotFoundError:
            return None
def lookup_utc_offset(zone: str) -> int | None:
    """Converts an IANA spec timezone into an UTC offset"""
    rn = datetime.now(UTC)
    utcdiff = ZoneInfo(zone).utcoffset(rn)
    return utcdiff.total_seconds() // (60*60)

async def update_db():
    global _reader, _lock, _github_repo

    while _github_repo is None:
        try:
            _github_repo = await to_thread(lambda: Github().get_repo("P3TERX/GeoLite.mmdb"))
        except Exception:
            _logger.error(f"Failed to get GeoLite repository, retrying in 1 minute")
            await sleep(60)

    while True:
        try:
            latest = await to_thread(_github_repo.get_latest_release)
            if not _db_id.exists():
                _db_id.write_text("0")
            if not _db.exists() or latest.id != int(_db_id.read_text()):
                for asset in latest.assets:
                    if asset.name != "GeoLite2-City.mmdb":
                        continue
                    await to_thread(lambda: asset.download_asset(_db_tmp))
                    with _lock:
                        file_replace(_db_tmp, _db)
                        _db_id.write_text(str(latest.id))
                        if _reader is not None:
                            _reader.close()
                            _reader = None
                    break
                else:
                    _logger.error(f"No file under the name 'GeoLite2-City.mmdb' found under the latest release ({latest.url})\nRetrying in 1 hour")
                    await sleep(1*60*60)
                    continue
            await sleep(12*60*60)
        except Exception:
            _logger.exception("Failed to get repository's latest release, retrying in 5 minutes")
            await sleep(5*60)
            continue
