from telegram.ext import ApplicationBuilder, CommandHandler

from airguard.config import TELEGRAM_TOKEN
from airguard.db.models import init_db
from airguard.bot.handlers import start, check, settings, report


def main() -> None:
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CommandHandler("report", report))
    app.run_polling()


if __name__ == "__main__":
    main()
