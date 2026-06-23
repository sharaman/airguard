from airguard.tools.calculator_tool import calculate_score
from airguard.rag.retriever import search_rag
from airguard.graph.nodes import report_node

TEST_CASES = [
    {
        "id": "TC01",
        "description": "Все показатели в норме — алерт не нужен",
        "input": {
            "air_data": {"pm25": 10, "pm10": 20, "no2": 15, "pollen_tree": 1, "uv_index": 3},
            "user_profile": {"diagnosis": "нет", "thresholds": {"pm25_warn": 50}},
        },
        "expected_alert_type": "ok",
        "expected_contains": [],
    },
    {
        "id": "TC02",
        "description": "PM2.5 сильно превышает порог для астматика",
        "input": {
            "air_data": {"pm25": 120, "pm10": 80, "no2": 30, "pollen_tree": 1, "uv_index": 3},
            "user_profile": {"diagnosis": "астма", "thresholds": {"pm25_warn": 50, "pm25_danger": 100}},
        },
        "expected_alert_type": "urgent",
        "expected_contains": ["PM2.5"],
    },
    {
        "id": "TC03",
        "description": "Умеренное превышение — warning, не urgent",
        "input": {
            "air_data": {"pm25": 65, "pm10": 50, "no2": 20, "pollen_tree": 1, "uv_index": 4},
            "user_profile": {"diagnosis": "нет", "thresholds": {"pm25_warn": 50, "pm25_danger": 100}},
        },
        "expected_alert_type": "warning",
        "expected_contains": ["PM2.5"],
    },
    {
        "id": "TC04",
        "description": "Высокая пыльца для аллергика",
        "input": {
            "air_data": {"pm25": 15, "pm10": 20, "no2": 10, "pollen_tree": 60, "uv_index": 5},
            "user_profile": {"diagnosis": "ринит", "allergens": ["пыльца_деревьев"], "thresholds": {"pollen_tree_warn": 30}},
        },
        "expected_alert_type": "warning",
        "expected_contains": ["пыльц"],
    },
    {
        "id": "TC05",
        "description": "Низкая пыльца, нет аллергии — ok",
        "input": {
            "air_data": {"pm25": 15, "pm10": 20, "no2": 10, "pollen_tree": 5, "uv_index": 5},
            "user_profile": {"diagnosis": "нет", "allergens": [], "thresholds": {}},
        },
        "expected_alert_type": "ok",
        "expected_contains": [],
    },
    {
        "id": "TC06",
        "description": "Аномальный рост PM2.5 — должна быть причина",
        "input": {
            "air_data": {"pm25": 180, "pm10": 100, "no2": 40, "pollen_tree": 1, "uv_index": 3},
            "anomaly": {"is_anomaly": True, "z_score": 3.8},
            "user_profile": {"diagnosis": "астма", "thresholds": {"pm25_warn": 50}},
        },
        "expected_alert_type": "urgent",
        "expected_contains": [],
    },
    {
        "id": "TC07",
        "description": "Небольшое превышение без аномалии",
        "input": {
            "air_data": {"pm25": 60, "pm10": 45, "no2": 20, "pollen_tree": 1, "uv_index": 3},
            "anomaly": {"is_anomaly": False, "z_score": 0.8},
            "user_profile": {"diagnosis": "нет", "thresholds": {"pm25_warn": 50}},
        },
        "expected_alert_type": "warning",
        "expected_not_contains": ["аномальн"],
    },
    {
        "id": "TC08",
        "description": "Тренд ухудшения → превентивный алерт",
        "input": {
            "air_data": {"pm25": 35, "pm10": 20, "no2": 15, "pollen_tree": 1, "uv_index": 3},
            "trend": {"direction": "up", "rate_per_hour": 18, "forecast_2h": 71},
            "user_profile": {"diagnosis": "нет", "thresholds": {"pm25_warn": 50}},
        },
        "expected_alert_type": "preventive",
        "expected_contains": [],
    },
    {
        "id": "TC09",
        "description": "Тренд роста, но прогноз ниже порога — ok",
        "input": {
            "air_data": {"pm25": 35, "pm10": 20, "no2": 15, "pollen_tree": 1, "uv_index": 3},
            "trend": {"direction": "up", "rate_per_hour": 5, "forecast_2h": 45},
            "user_profile": {"diagnosis": "нет", "thresholds": {"pm25_warn": 50}},
        },
        "expected_alert_type": "ok",
        "expected_contains": [],
    },
    {
        "id": "TC10",
        "description": "UV-индекс экстремальный — упоминание защиты от солнца",
        "input": {
            "air_data": {"pm25": 12, "pm10": 18, "no2": 10, "pollen_tree": 1, "uv_index": 11},
            "user_profile": {"diagnosis": "нет", "thresholds": {"uv_warn": 6}},
        },
        "expected_alert_type": "warning",
        "expected_contains": ["UV"],
    },
]


def build_test_state(inp: dict) -> dict:
    air_data = inp["air_data"]
    user_profile = inp["user_profile"]
    score = inp.get("score") or calculate_score(air_data, user_profile)
    anomaly = inp.get("anomaly", {"is_anomaly": False, "z_score": 0.0})
    trend = inp.get("trend", {"direction": "stable", "rate_per_hour": 0.0, "forecast_2h": 0.0})

    rag_context = ""
    if anomaly.get("is_anomaly") or score["risk_level"] == "danger":
        exceeded = score.get("exceeded_params", [])
        diagnosis = user_profile.get("diagnosis", "нет")
        rag_context = search_rag(f"аномалия {' '.join(exceeded)} {diagnosis} рекомендации")

    rag_trend_context = ""
    if trend["direction"] == "up" and trend["forecast_2h"] > user_profile.get("thresholds", {}).get("pm25_warn", 25):
        diagnosis = user_profile.get("diagnosis", "нет")
        rag_trend_context = search_rag(f"тренд ухудшения воздуха прогноз {diagnosis}")

    return {
        "user_id": 0,
        "lat": 0.0,
        "lon": 0.0,
        "user_profile": user_profile,
        "air_data": air_data,
        "score": score,
        "anomaly": anomaly,
        "trend": trend,
        "rag_context": rag_context,
        "rag_trend_context": rag_trend_context,
    }


def run_benchmark():
    results = []
    for tc in TEST_CASES:
        state = build_test_state(tc["input"])
        output = report_node(state)

        passed = True
        failures = []

        if output["alert_type"] != tc["expected_alert_type"]:
            passed = False
            failures.append(f"alert_type: got '{output['alert_type']}', expected '{tc['expected_alert_type']}'")

        for kw in tc.get("expected_contains", []):
            if kw.lower() not in output["alert_message"].lower():
                passed = False
                failures.append(f"missing keyword: '{kw}'")

        for kw in tc.get("expected_not_contains", []):
            if kw.lower() in output["alert_message"].lower():
                passed = False
                failures.append(f"unexpected keyword: '{kw}'")

        results.append({"id": tc["id"], "passed": passed, "failures": failures})
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {tc['id']}: {tc['description']}")
        if failures:
            for f in failures:
                print(f"       {f}")

    passed_count = sum(r["passed"] for r in results)
    total = len(results)
    print(f"\nSuccess rate: {passed_count}/{total} ({passed_count / total * 100:.0f}%)")
    return results


if __name__ == "__main__":
    run_benchmark()
