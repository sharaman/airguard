import statistics

from airguard.db.repository import get_readings

DEFAULT_THRESHOLDS = {
    "pm25": 25.0,
    "pm10": 50.0,
    "no2": 40.0,
    "o3": 100.0,
    "pollen_tree": 30.0,
    "pollen_grass": 50.0,
    "uv_index": 6.0,
}

BASE_WEIGHTS = {"uv_index": 2.0}

DIAGNOSIS_WEIGHTS = {
    "астма": {"pm25": 2.0, "pm10": 1.5, "o3": 1.5, "no2": 1.3},
    "ринит": {"pollen_tree": 2.0, "pollen_grass": 2.0, "pm10": 1.2},
    "нет": {},
}

BASE_PENALTY = 15.0


def calculate_score(air_data: dict, user_profile: dict) -> dict:
    diagnosis = user_profile.get("diagnosis", "нет")
    weights = DIAGNOSIS_WEIGHTS.get(diagnosis, {})
    custom_thresholds = user_profile.get("thresholds", {})

    score = 100.0
    exceeded = []

    for param, default_thr in DEFAULT_THRESHOLDS.items():
        value = air_data.get(param)
        if value is None:
            continue

        threshold = custom_thresholds.get(f"{param}_warn", default_thr)
        if value <= threshold:
            continue

        exceeded.append(param)
        ratio = min(value / threshold, 5.0)
        weight = weights.get(param, BASE_WEIGHTS.get(param, 1.0))
        score -= (ratio - 1.0) * BASE_PENALTY * weight

    score = max(0.0, min(100.0, score))

    if score < 50:
        risk_level = "danger"
    elif score < 80:
        risk_level = "warning"
    else:
        risk_level = "ok"

    return {
        "score": round(score, 1),
        "risk_level": risk_level,
        "exceeded_params": exceeded,
    }


def detect_anomaly_zscore(value: float, param: str, user_id: int) -> dict:
    history = get_readings(user_id, param, days=30)
    if len(history) < 5:
        return {"is_anomaly": False, "z_score": 0.0}

    mean = statistics.mean(history)
    stdev = statistics.pstdev(history)
    z = (value - mean) / (stdev + 1e-9)

    return {"is_anomaly": abs(z) > 2.0, "z_score": round(z, 2)}
