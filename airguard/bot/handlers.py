import logging
import time

from telegram import Update
from telegram.ext import ContextTypes

from langfuse.langchain import CallbackHandler as LangfuseCallback

from airguard.db.repository import get_user, save_user, save_measurement, update_user, get_last_measurements
from airguard.graph.builder import build_graph

logger = logging.getLogger(__name__)

graph = build_graph()

DEFAULT_LAT = 55.75
DEFAULT_LON = 37.62
RATE_LIMIT_SECONDS = 10

_last_check: dict[int, float] = {}


def _build_user_profile(user: dict) -> dict:
    profile: dict = {"diagnosis": user.get("diagnosis") or "нет", "allergens": [], "thresholds": {}}
    if user.get("allergens"):
        profile["allergens"] = [a.strip() for a in user["allergens"].split(",")]
    for key in ("pm25", "pm10", "no2", "o3"):
        val = user.get(f"{key}_threshold")
        if val is not None:
            profile["thresholds"][f"{key}_warn"] = val
    return profile


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    save_user(user_id)
    await update.message.reply_text(
        "Привет! Я AirGuard — бот мониторинга качества воздуха.\n"
        "Используй /check, чтобы проверить воздух рядом с тобой."
    )


SETTINGS_HELP = (
    "Настройки профиля:\n"
    "/settings location <широта> <долгота>\n"
    "/settings diagnosis <астма|ринит|нет>\n"
    "/settings allergens <аллерген1,аллерген2>\n\n"
    "Пример: /settings location 55.75 37.62"
)


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user = get_user(user_id)
    if user is None:
        await update.message.reply_text("Сначала нажми /start.")
        return

    args = context.args or []
    if not args:
        lat = user.get("lat") or DEFAULT_LAT
        lon = user.get("lon") or DEFAULT_LON
        diag = user.get("diagnosis") or "нет"
        allerg = user.get("allergens") or "не указаны"
        await update.message.reply_text(
            f"Локация: {lat}, {lon}\n"
            f"Диагноз: {diag}\n"
            f"Аллергены: {allerg}\n\n"
            f"{SETTINGS_HELP}"
        )
        return

    cmd = args[0].lower()

    if cmd == "location" and len(args) == 3:
        try:
            lat, lon = float(args[1]), float(args[2])
        except ValueError:
            await update.message.reply_text("Координаты должны быть числами.")
            return
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            await update.message.reply_text("Широта: -90..90, долгота: -180..180.")
            return
        update_user(user_id, lat=lat, lon=lon)
        await update.message.reply_text(f"Локация обновлена: {lat}, {lon}")

    elif cmd == "diagnosis" and len(args) == 2:
        diag = args[1].lower()
        if diag not in ("астма", "ринит", "нет"):
            await update.message.reply_text("Допустимые значения: астма, ринит, нет")
            return
        update_user(user_id, diagnosis=diag)
        await update.message.reply_text(f"Диагноз обновлён: {diag}")

    elif cmd == "allergens" and len(args) >= 2:
        allergens = " ".join(args[1:])
        update_user(user_id, allergens=allergens)
        await update.message.reply_text(f"Аллергены обновлены: {allergens}")

    else:
        await update.message.reply_text(SETTINGS_HELP)


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if get_user(user_id) is None:
        await update.message.reply_text("Сначала нажми /start.")
        return

    rows = get_last_measurements(user_id, limit=5)
    if not rows:
        await update.message.reply_text("Пока нет замеров. Используй /check.")
        return

    lines = ["Последние замеры:\n"]
    for r in rows:
        ts = r["created_at"][:16].replace("T", " ")
        risk = r["risk_level"] or "?"
        sc = r["score"]
        sc_str = f"{sc:.0f}" if sc is not None else "?"
        lines.append(f"{ts}  score={sc_str}  [{risk}]")

    await update.message.reply_text("\n".join(lines))


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user = get_user(user_id)
    if user is None:
        await update.message.reply_text("Сначала нажми /start.")
        return

    now = time.monotonic()
    last = _last_check.get(user_id, 0)
    if now - last < RATE_LIMIT_SECONDS:
        wait = int(RATE_LIMIT_SECONDS - (now - last)) + 1
        await update.message.reply_text(f"Подожди {wait} сек. перед следующей проверкой.")
        return
    _last_check[user_id] = now

    lat = user.get("lat") or DEFAULT_LAT
    lon = user.get("lon") or DEFAULT_LON
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        await update.message.reply_text("Некорректные координаты. Обнови через /settings location.")
        return

    await update.message.reply_text("Данные собираются...")

    state = {
        "user_id": user_id,
        "lat": lat,
        "lon": lon,
        "user_profile": _build_user_profile(user),
    }

    handler = LangfuseCallback()

    try:
        result = await graph.ainvoke(
            state,
            config={"callbacks": [handler]},
        )
    except Exception:
        logger.exception("Graph invocation failed")
        await update.message.reply_text("Не удалось получить данные. Попробуйте позже.")
        return

    air = result.get("air_data", {})
    score = result.get("score", {})
    save_measurement(user_id, {**air, "score": score.get("score"), "risk_level": score.get("risk_level"), "alert_type": result.get("alert_type")})

    await update.message.reply_text(result.get("alert_message", "Нет данных."))
