from typing import Literal, TypedDict


class AirGuardState(TypedDict, total=False):
    # входные данные
    user_id: int
    lat: float
    lon: float
    user_profile: dict

    # заполняется узлами
    air_data: dict
    score: dict
    anomaly: dict
    trend: dict
    rag_context: str
    rag_trend_context: str

    # итог
    alert_type: Literal["ok", "warning", "urgent", "preventive"]
    alert_message: str
