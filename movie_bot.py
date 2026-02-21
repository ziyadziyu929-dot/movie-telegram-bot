import os
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from apscheduler.schedulers.background import BackgroundScheduler

# ---------------- LOAD ENV ----------------
BOT_TOKEN = os.environ.get("8292328042:AAHOXPdEamr_7tC9lvxfkC2wQrqKbJyAoUc")
OMDB_API = os.environ.get("fbb246db")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN not found in environment variables")

if not OMDB_API:
    raise RuntimeError("❌ OMDB_API not found in environment variables")


# ---------------- HELPERS ----------------
def fetch_movies(query="Batman"):
    """
    Fetch top 5 movies using OMDb search
    (OMDb has no 'latest movies' endpoint)
    """
    url = f"http://www.omdbapi.com/?apikey={OMDB_API}&s={query}"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
    except Exception:
        return []

    if data.get("Response") == "False":
        return []

    return data.get("Search", [])[:5]


def search_movie(title):
    """
    Fetch full movie details by title
    """
    url = f"http://www.omdbapi.com/?apikey={OMDB_API}&t={title}"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
    except Exception:
        return None

    if data.get("Response") == "False":
        return None

    return data


# ---------------- COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 *Welcome to Movie Bot!*\n\n"
        "Commands:\n"
        "/latest – Top movies\n"
        "/search <movie name> – Movie details\n"
        "/subscribe – Daily updates",
        parse_mode="Markdown"
    )


async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movies = fetch_movies()

    if not movies:
        await update.message.reply_text("❌ Unable to fetch movies.")
        return

    for movie in movies:
        caption = (
            f"🎬 *{movie.get('Title')}*\n"
            f"🗓 Year: {movie.get('Year')}\n"
            f"🆔 IMDb ID: {movie.get('imdbID')}"
        )

        poster = movie.get("Poster")
        if poster and poster != "N/A":
            await update.message.reply_photo(
                photo=poster,
                caption=caption,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(caption, parse_mode="Markdown")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search movie_name")
        return

    query = " ".join(context.args)
    movie = search_movie(query)

    if not movie:
        await update.message.reply_text("❌ Movie not found.")
        return

    caption = (
        f"🎬 *{movie.get('Title')}*\n"
        f"⭐ IMDb Rating: {movie.get('imdbRating', 'N/A')}\n"
        f"🗓 Year: {movie.get('Year')}\n\n"
        f"{movie.get('Plot', 'No description available')}"
    )

    poster = movie.get("Poster")
    if poster and poster != "N/A":
        await update.message.reply_photo(
            photo=poster,
            caption=caption[:1024],
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(caption, parse_mode="Markdown")


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subs = context.application.bot_data.setdefault("subscribers", set())

    subs.add(chat_id)
    await update.message.reply_text("✅ Subscribed to daily movie updates!")


# ---------------- DAILY UPDATE ----------------
async def send_daily(application):
    subs = application.bot_data.get("subscribers", set())
    if not subs:
        return

    movies = fetch_movies("Hollywood")
    if not movies:
        return

    text = "🔥 *Daily Movie Update*\n\n"
    for movie in movies:
        text += f"🎬 {movie.get('Title')} ({movie.get('Year')})\n"

    for chat_id in subs:
        try:
            await application.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown"
            )
        except Exception:
            pass


def schedule_daily(application):
    application.create_task(send_daily(application))


# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("latest", latest))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("subscribe", subscribe))

    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: schedule_daily(app), "interval", hours=24)
    scheduler.start()

    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()