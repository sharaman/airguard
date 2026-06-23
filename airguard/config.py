from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
OPENAQ_API_KEY = os.environ["OPENAQ_API_KEY"]
OPENWEATHER_API_KEY = os.environ["OPENWEATHER_API_KEY"]
OPENUV_API_KEY = os.environ["OPENUV_API_KEY"]

LANGFUSE_PUBLIC_KEY = os.environ["LANGFUSE_PUBLIC_KEY"]
LANGFUSE_SECRET_KEY = os.environ["LANGFUSE_SECRET_KEY"]
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

DB_PATH = Path(os.environ.get("DB_PATH", "db/airguard.db"))

HTTPX_TIMEOUT = 10

LLM_MODEL = "llama-3.3-70b-versatile"
