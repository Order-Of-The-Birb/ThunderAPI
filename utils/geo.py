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

_logger = getLogger(__name__)
_db = Path(__file__).parent / "GeoLite2-City.mmdb"
_db_tmp = _db.parent / "GeoLite2-City.mmdb.tmp"
_db_id = _db.parent / "GeoLite2-City.hash"
_reader = None
_lock = Lock()

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
    global _reader, _lock

    iter_cnt = 0
    while True:
        try:
            github_repo = await to_thread(lambda: Github().get_repo("P3TERX/GeoLite.mmdb"))
            break
        except Exception:
            _logger.error(f"Failed to get repository on try {iter_cnt}")
            if iter_cnt > 5:
                raise RuntimeError("Could not obtain geolocation repository data")
            iter_cnt += 1
            await sleep(30)
    del iter_cnt

    if not _db.exists():
        try:
            latest = await to_thread(github_repo.get_latest_release)
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
                raise RuntimeError(f"No file under the name 'GeoLite2-City.mmdb' found under the latest release ({latest.url})")
            await sleep(12*60*60)
        except Exception:
            _logger.exception("Failed to get repository's latest release")
            await sleep(60*60)

    while True:
        try:
            latest = await to_thread(github_repo.get_latest_release)
            if latest.id != int(_db_id.read_text()):
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
            _logger.exception("Failed to get repository's latest release")
            await sleep(60*60)
            continue
