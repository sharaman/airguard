from airguard.eval.benchmark import build_test_state, TEST_CASES
from airguard.graph.nodes import report_node, _determine_alert_type
from airguard.tools.calculator_tool import calculate_score


def test_urgent_when_danger():
    state = build_test_state({
        "air_data": {"pm25": 200, "pm10": 80, "no2": 30, "pollen_tree": 1, "uv_index": 3},
        "user_profile": {"diagnosis": "астма", "thresholds": {"pm25_warn": 50}},
    })
    assert state["score"]["risk_level"] == "danger"
    assert _determine_alert_type(state) == "urgent"


def test_ok_when_all_normal():
    state = build_test_state({
        "air_data": {"pm25": 10, "pm10": 20, "no2": 15, "pollen_tree": 1, "uv_index": 3},
        "user_profile": {"diagnosis": "нет", "thresholds": {}},
    })
    assert _determine_alert_type(state) == "ok"


def test_rag_context_on_anomaly():
    state = build_test_state({
        "air_data": {"pm25": 180, "pm10": 100, "no2": 40, "pollen_tree": 1, "uv_index": 3},
        "anomaly": {"is_anomaly": True, "z_score": 3.8},
        "user_profile": {"diagnosis": "астма", "thresholds": {"pm25_warn": 50}},
    })
    assert state.get("rag_context"), "RAG не был вызван при аномалии"


def test_rag_context_on_danger():
    state = build_test_state({
        "air_data": {"pm25": 200, "pm10": 80, "no2": 30, "pollen_tree": 1, "uv_index": 3},
        "user_profile": {"diagnosis": "астма", "thresholds": {"pm25_warn": 50}},
    })
    assert state.get("rag_context"), "RAG не был вызван при danger"


def test_no_rag_when_ok():
    state = build_test_state({
        "air_data": {"pm25": 10, "pm10": 20, "no2": 15, "pollen_tree": 1, "uv_index": 3},
        "user_profile": {"diagnosis": "нет", "thresholds": {}},
    })
    assert not state.get("rag_context"), "RAG вызван без необходимости"


def test_message_not_empty():
    for tc in TEST_CASES:
        state = build_test_state(tc["input"])
        output = report_node(state)
        assert output["alert_message"].strip(), f"Пустое сообщение в {tc['id']}"


def test_score_boundaries():
    ok = calculate_score({"pm25": 10}, {"diagnosis": "нет"})
    assert ok["risk_level"] == "ok"

    warn = calculate_score({"pm25": 65}, {"diagnosis": "нет"})
    assert warn["risk_level"] == "warning"

    danger = calculate_score(
        {"pm25": 120, "pm10": 80},
        {"diagnosis": "астма", "thresholds": {"pm25_warn": 50, "pm10_warn": 50}},
    )
    assert danger["risk_level"] == "danger"


def test_preventive_logic():
    state = build_test_state({
        "air_data": {"pm25": 35, "pm10": 20, "no2": 15, "pollen_tree": 1, "uv_index": 3},
        "trend": {"direction": "up", "rate_per_hour": 18, "forecast_2h": 71},
        "user_profile": {"diagnosis": "нет", "thresholds": {"pm25_warn": 50}},
    })
    assert _determine_alert_type(state) == "preventive"

    state_no = build_test_state({
        "air_data": {"pm25": 35, "pm10": 20, "no2": 15, "pollen_tree": 1, "uv_index": 3},
        "trend": {"direction": "up", "rate_per_hour": 5, "forecast_2h": 45},
        "user_profile": {"diagnosis": "нет", "thresholds": {"pm25_warn": 50}},
    })
    assert _determine_alert_type(state_no) == "ok"


TESTS = [
    test_urgent_when_danger,
    test_ok_when_all_normal,
    test_rag_context_on_anomaly,
    test_rag_context_on_danger,
    test_no_rag_when_ok,
    test_message_not_empty,
    test_score_boundaries,
    test_preventive_logic,
]


def run_asserts():
    passed = 0
    for test in TESTS:
        name = test.__name__
        try:
            test()
            print(f"[PASS] {name}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {name}: {e}")
        except Exception as e:
            print(f"[ERROR] {name}: {e}")

    print(f"\n{passed}/{len(TESTS)} passed")


if __name__ == "__main__":
    run_asserts()
