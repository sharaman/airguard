import logging

import httpx

from airguard.config import OPENUV_API_KEY, HTTPX_TIMEOUT

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
OPENUV_URL = "https://api.openuv.io/api/v1/uv"


def _fetch_pollen(lat: float, lon: float) -> dict:
    try:
        resp = httpx.get(
            OPEN_METEO_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "birch_pollen,grass_pollen",
            },
            timeout=HTTPX_TIMEOUT,
        )
        resp.raise_for_status()
        current = resp.json().get("current", {})
        return {
            "pollen_tree": current.get("birch_pollen"),
            "pollen_grass": current.get("grass_pollen"),
        }
    except httpx.HTTPError as e:
        logger.warning("Open-Meteo pollen request failed: %s", e)
        return {"pollen_tree": None, "pollen_grass": None}


def _fetch_uv(lat: float, lon: float) -> dict:
    try:
        resp = httpx.get(
            OPENUV_URL,
            params={"lat": lat, "lng": lon},
            headers={"x-access-token": OPENUV_API_KEY},
            timeout=HTTPX_TIMEOUT,
        )
        resp.raise_for_status()
        uv = resp.json().get("result", {}).get("uv")
        return {"uv_index": round(uv, 1) if uv is not None else None}
    except httpx.HTTPError as e:
        logger.warning("OpenUV request failed: %s", e)
        return {"uv_index": None}


def get_pollen_and_uv(lat: float, lon: float) -> dict:
    pollen = _fetch_pollen(lat, lon)
    uv = _fetch_uv(lat, lon)
    return {**pollen, **uv}
