import re

import numpy as np
from langchain_groq import ChatGroq
from langfuse.langchain import CallbackHandler as LangfuseCallback

from airguard.config import GROQ_API_KEY, LLM_MODEL
from airguard.db.repository import get_recent_readings
from airguard.graph.state import AirGuardState
from airguard.rag.retriever import search_rag
from airguard.tools.aqi_tool import get_air_quality
from airguard.tools.calculator_tool import calculate_score, detect_anomaly_zscore
from airguard.tools.pollen_uv_tool import get_pollen_and_uv

llm = ChatGroq(model=LLM_MODEL, temperature=0, api_key=GROQ_API_KEY)
langfuse_handler = LangfuseCallback()

REPORT_PROMPT = """\
Сформируй короткое Telegram-сообщение (до 10 строк) о качестве воздуха.
Тип алерта: [{alert_type}]. Начни сообщение с этого тега.

Показатели: {air_data}
Персональный score: {score}
Аномалия: {anomaly}
Тренд: {trend}
Рекомендации из базы знаний: {rag_context}
Профиль пользователя: {user_profile}

Правила:
- Пиши на русском языке, кратко и по делу.
- Первая строка — [{alert_type}], затем текст.
- ОБЯЗАТЕЛЬНО упомяни каждый превышенный параметр из exceeded_params по названию (PM2.5, PM10, NO2, O3, UV, пыльца).
- Дай конкретные рекомендации с учётом диагноза пользователя.
"""


def collect_node(state: AirGuardState) -> AirGuardState:
    air = get_air_quality(state["lat"], state["lon"])
    env = get_pollen_and_uv(state["lat"], state["lon"])
    return {"air_data": {**air, **env}}


def analyze_node(state: AirGuardState) -> AirGuardState:
    score = calculate_score(state["air_data"], state["user_profile"])
    return {"score": score}


def anomaly_node(state: AirGuardState) -> AirGuardState:
    exceeded = state["score"].get("exceeded_params", [])
    param = exceeded[0] if exceeded else "pm25"
    value = state["air_data"].get(param, 0) or 0
    anomaly = detect_anomaly_zscore(value, param, state["user_id"])
    return {"anomaly": anomaly}


def rag_node(state: AirGuardState) -> AirGuardState:
    exceeded = state["score"].get("exceeded_params", [])
    diagnosis = state["user_profile"].get("diagnosis", "нет")
    query = f"аномалия {' '.join(exceeded)} {diagnosis} рекомендации"
    return {"rag_context": search_rag(query)}


def trend_node(state: AirGuardState) -> AirGuardState:
    history = get_recent_readings(state["user_id"], "pm25", hours=3)
    if len(history) < 3:
        return {"trend": {"direction": "stable", "rate_per_hour": 0.0, "forecast_2h": 0.0}}

    slope = np.polyfit(range(len(history)), history, 1)[0]
    rate = slope * 4

    if slope > 0.3:
        direction = "up"
    elif slope < -0.3:
        direction = "down"
    else:
        direction = "stable"

    return {"trend": {
        "direction": direction,
        "rate_per_hour": round(float(rate), 2),
        "forecast_2h": round(float(history[-1] + rate * 2), 1),
    }}


def rag_trend_node(state: AirGuardState) -> AirGuardState:
    diagnosis = state["user_profile"].get("diagnosis", "нет")
    query = f"тренд ухудшения воздуха прогноз {diagnosis} рекомендации"
    return {"rag_trend_context": search_rag(query)}


def _determine_alert_type(state: AirGuardState) -> str:
    score = state.get("score", {})
    risk = score.get("risk_level", "ok")
    if risk == "danger":
        return "urgent"
    if risk == "warning" or score.get("exceeded_params"):
        return "warning"
    trend = state.get("trend", {})
    threshold = state["user_profile"].get("thresholds", {}).get("pm25_warn", 25.0)
    if trend.get("direction") == "up" and trend.get("forecast_2h", 0) > threshold:
        return "preventive"
    return "ok"


def report_node(state: AirGuardState) -> AirGuardState:
    alert_type = _determine_alert_type(state)

    rag = state.get("rag_context", "")
    rag_trend = state.get("rag_trend_context", "")
    combined_rag = f"{rag}\n{rag_trend}".strip()

    prompt = REPORT_PROMPT.format(
        alert_type=alert_type,
        air_data=state["air_data"],
        score=state["score"],
        anomaly=state.get("anomaly", {}),
        trend=state.get("trend", {}),
        rag_context=combined_rag or "нет данных",
        user_profile=state["user_profile"],
    )

    response = llm.invoke(prompt, config={"callbacks": [langfuse_handler]})

    return {"alert_type": alert_type, "alert_message": response.content}
