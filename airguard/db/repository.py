import sqlite3

from airguard.config import DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_user(user_id: int) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_user(user_id: int) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
        )
        conn.commit()
    finally:
        conn.close()


def get_readings(user_id: int, param: str, days: int = 30) -> list[float]:
    allowed = {"pm25", "pm10", "no2", "o3", "pollen_tree", "pollen_grass", "uv_index", "score"}
    if param not in allowed:
        return []
    conn = _connect()
    try:
        rows = conn.execute(
            f"SELECT {param} FROM measurements "
            f"WHERE user_id = ? AND created_at >= datetime('now', ?) AND {param} IS NOT NULL "
            "ORDER BY created_at",
            (user_id, f"-{days} days"),
        ).fetchall()
        return [float(r[0]) for r in rows]
    finally:
        conn.close()


def update_user(user_id: int, **fields) -> None:
    allowed = {"lat", "lon", "diagnosis", "allergens",
               "pm25_threshold", "pm10_threshold", "no2_threshold", "o3_threshold"}
    to_update = {k: v for k, v in fields.items() if k in allowed}
    if not to_update:
        return
    cols = ", ".join(f"{k} = ?" for k in to_update)
    vals = list(to_update.values()) + [user_id]
    conn = _connect()
    try:
        conn.execute(f"UPDATE users SET {cols} WHERE user_id = ?", vals)
        conn.commit()
    finally:
        conn.close()


def get_last_measurements(user_id: int, limit: int = 5) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT pm25, pm10, no2, o3, pollen_tree, pollen_grass, uv_index, "
            "score, risk_level, alert_type, created_at "
            "FROM measurements WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_measurement(user_id: int, data: dict) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO measurements "
            "(user_id, pm25, pm10, no2, o3, pollen_tree, pollen_grass, uv_index, score, risk_level, alert_type) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                data.get("pm25"), data.get("pm10"), data.get("no2"), data.get("o3"),
                data.get("pollen_tree"), data.get("pollen_grass"), data.get("uv_index"),
                data.get("score"), data.get("risk_level"), data.get("alert_type"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_readings(user_id: int, param: str, hours: int = 3) -> list[float]:
    allowed = {"pm25", "pm10", "no2", "o3", "pollen_tree", "pollen_grass", "uv_index", "score"}
    if param not in allowed:
        return []
    conn = _connect()
    try:
        rows = conn.execute(
            f"SELECT {param} FROM measurements "
            f"WHERE user_id = ? AND created_at >= datetime('now', ?) AND {param} IS NOT NULL "
            "ORDER BY created_at",
            (user_id, f"-{hours} hours"),
        ).fetchall()
        return [float(r[0]) for r in rows]
    finally:
        conn.close()
