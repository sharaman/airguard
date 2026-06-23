import logging
import time

from airguard.db.models import init_db
from airguard.graph.builder import build_graph

logging.basicConfig(level=logging.WARNING)

SCENARIOS = [
    {
        "name": "Moscow (normal conditions)",
        "state": {
            "user_id": 0,
            "lat": 55.75,
            "lon": 37.62,
            "user_profile": {"diagnosis": "нет", "allergens": [], "thresholds": {}},
        },
    },
    {
        "name": "Delhi (high pollution, asthma)",
        "state": {
            "user_id": 0,
            "lat": 28.6,
            "lon": 77.2,
            "user_profile": {
                "diagnosis": "астма",
                "allergens": [],
                "thresholds": {"pm25_warn": 50},
            },
        },
    },
    {
        "name": "Reykjavik (clean air, allergy)",
        "state": {
            "user_id": 0,
            "lat": 64.15,
            "lon": -21.95,
            "user_profile": {
                "diagnosis": "ринит",
                "allergens": ["пыльца_деревьев"],
                "thresholds": {},
            },
        },
    },
]

REQUIRED_FIELDS = ["air_data", "score", "anomaly", "trend", "alert_type", "alert_message"]
VALID_ALERT_TYPES = {"ok", "warning", "urgent", "preventive"}


def run_e2e():
    init_db()
    graph = build_graph()
    passed = 0

    for sc in SCENARIOS:
        name = sc["name"]
        print(f"\n--- {name} ---")
        start = time.time()

        try:
            result = graph.invoke(sc["state"])
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
            continue

        elapsed = time.time() - start
        failures = []

        for field in REQUIRED_FIELDS:
            if field not in result:
                failures.append(f"missing field: {field}")

        if result.get("alert_type") not in VALID_ALERT_TYPES:
            failures.append(f"invalid alert_type: {result.get('alert_type')}")

        msg = result.get("alert_message", "")
        if not msg or len(msg) < 10:
            failures.append("alert_message too short or empty")

        air = result.get("air_data", {})
        if not isinstance(air, dict):
            failures.append("air_data is not a dict")

        score = result.get("score", {})
        if score.get("score") is None:
            failures.append("score is None")

        if failures:
            print(f"[FAIL] {', '.join(failures)}")
        else:
            print(f"[PASS] alert={result['alert_type']}  score={score.get('score')}  time={elapsed:.1f}s")
            passed += 1

        print(f"  air_data: {air}")
        print(f"  message: {msg[:120]}...")

    print(f"\n{passed}/{len(SCENARIOS)} scenarios passed")


if __name__ == "__main__":
    run_e2e()
