from unittest.mock import patch

from airguard.graph.builder import build_graph


def _make_state(**overrides):
    state = {
        "user_id": 0,
        "lat": 55.75,
        "lon": 37.62,
        "user_profile": {"diagnosis": "нет", "allergens": [], "thresholds": {}},
    }
    state.update(overrides)
    return state


def test_aqi_tool_called():
    with patch("airguard.graph.nodes.get_air_quality") as mock_aqi, \
         patch("airguard.graph.nodes.get_pollen_and_uv") as mock_env:
        mock_aqi.return_value = {"pm25": 10, "pm10": 20, "no2": 15, "o3": 30}
        mock_env.return_value = {"pollen_tree": 1, "pollen_grass": 1, "uv_index": 3}

        graph = build_graph()
        graph.invoke(_make_state())

        mock_aqi.assert_called_once_with(55.75, 37.62)
        mock_env.assert_called_once_with(55.75, 37.62)


def test_rag_not_called_when_ok():
    with patch("airguard.graph.nodes.get_air_quality") as mock_aqi, \
         patch("airguard.graph.nodes.get_pollen_and_uv") as mock_env, \
         patch("airguard.graph.nodes.search_rag") as mock_rag:
        mock_aqi.return_value = {"pm25": 10, "pm10": 20, "no2": 15, "o3": 30}
        mock_env.return_value = {"pollen_tree": 1, "pollen_grass": 1, "uv_index": 3}

        graph = build_graph()
        graph.invoke(_make_state())

        mock_rag.assert_not_called()


def test_rag_called_when_danger():
    with patch("airguard.graph.nodes.get_air_quality") as mock_aqi, \
         patch("airguard.graph.nodes.get_pollen_and_uv") as mock_env, \
         patch("airguard.graph.nodes.search_rag") as mock_rag:
        mock_aqi.return_value = {"pm25": 200, "pm10": 80, "no2": 30, "o3": 10}
        mock_env.return_value = {"pollen_tree": 1, "pollen_grass": 1, "uv_index": 3}
        mock_rag.return_value = "Рекомендация: остаться дома."

        graph = build_graph()
        state = _make_state(user_profile={
            "diagnosis": "астма", "allergens": [], "thresholds": {"pm25_warn": 50},
        })
        result = graph.invoke(state)

        mock_rag.assert_called()
        assert result.get("rag_context"), "rag_context пуст при danger"


TESTS = [
    test_aqi_tool_called,
    test_rag_not_called_when_ok,
    test_rag_called_when_danger,
]


def run_tool_checks():
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
    run_tool_checks()
