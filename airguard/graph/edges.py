from airguard.graph.state import AirGuardState

DEFAULT_PM25_WARN = 25.0


def route_after_anomaly(state: AirGuardState) -> str:
    if state["anomaly"].get("is_anomaly") or state["score"]["risk_level"] == "danger":
        return "fetch_rag"
    return "detect_trend"


def route_after_trend(state: AirGuardState) -> str:
    trend = state["trend"]
    threshold = (
        state["user_profile"]
        .get("thresholds", {})
        .get("pm25_warn", DEFAULT_PM25_WARN)
    )
    if trend["direction"] == "up" and trend["forecast_2h"] > threshold:
        return "fetch_rag_trend"
    return "generate_report"
