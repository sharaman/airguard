import logging

import httpx

from airguard.config import OPENAQ_API_KEY, HTTPX_TIMEOUT

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openaq.org/v3"
PARAMS_OF_INTEREST = ("pm25", "pm10", "no2", "o3")
SEARCH_RADIUS = 25_000

EMPTY_RESULT: dict[str, float | None] = {p: None for p in PARAMS_OF_INTEREST}


def get_air_quality(lat: float, lon: float) -> dict:
    headers = {"X-API-Key": OPENAQ_API_KEY}

    try:
        resp = httpx.get(
            f"{BASE_URL}/locations",
            params={
                "coordinates": f"{lat},{lon}",
                "radius": SEARCH_RADIUS,
                "limit": 10,
            },
            headers=headers,
            timeout=HTTPX_TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("OpenAQ locations request failed: %s", e)
        return dict(EMPTY_RESULT)

    result: dict[str, float | None] = dict(EMPTY_RESULT)

    for loc in resp.json().get("results", []):
        sensor_map: dict[int, str] = {}
        for s in loc.get("sensors", []):
            name = s.get("parameter", {}).get("name", "")
            if name in PARAMS_OF_INTEREST and result[name] is None:
                sensor_map[s["id"]] = name

        if not sensor_map:
            continue

        try:
            latest = httpx.get(
                f"{BASE_URL}/locations/{loc['id']}/latest",
                headers=headers,
                timeout=HTTPX_TIMEOUT,
            )
            latest.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("OpenAQ latest request failed for location %s: %s", loc["id"], e)
            continue

        for r in latest.json().get("results", []):
            name = sensor_map.get(r["sensorsId"])
            if name and result[name] is None:
                result[name] = round(float(r["value"]), 1)

        if all(v is not None for v in result.values()):
            break

    return result
