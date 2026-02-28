import os
import requests

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ================= ENV VARIABLES =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OMDB_API = os.getenv("OMDB_API")

if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN missing")

if not OMDB_API:
    print("WARNING: OMDB_API missing (movie features limited)")


# ================= HELPERS =================

def fetch_movies(query="Batman"):
    """Fetch movie list from OMDB"""
    if not OMDB_API:
        return []

    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&s={query}"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()
    except Exception as e:
        print("Fetch error:", e)
        return []

    if data.get("Response") == "False":
        return []

    return data.get("Search", [])[:5]


def search_movie(title):
    """Fetch single movie details"""
    if not OMDB_API:
        return None

    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&t={title}"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()
    except Exception as e:
        print("Search error:", e)
        return None

    if data.get("Response") == "False":
        return None

    return data


# ================= COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Movie Bot is running!\n\n"
        "Commands:\n"
        "/latest - Latest movies\n"
        "/search <name> - Movie details\n"
        "/subscribe - Daily updates"
    )


async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):

    movies = fetch_movies()

    if not movies:
        await update.message.reply_text("❌ Cannot fetch movies")
        return

    for movie in movies:

        text = f"🎬 {movie['Title']} ({movie['Year']})"

        await update.message.reply_text(text)


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text("Usage: /search movie_name")
        return

    title = " ".join(context.args)

    movie = search_movie(title)

    if not movie:
        await update.message.reply_text("❌ Movie not found")
        return

    text = (
        f"🎬 {movie.get('Title')}\n"
        f"⭐ IMDb: {movie.get('imdbRating')}\n"
        f"📅 Year: {movie.get('Year')}\n\n"
        f"📝 {movie.get('Plot')}"
    )

    await update.message.reply_text(text)


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):

    subs = context.application.bot_data.setdefault("subscribers", set())

    subs.add(update.effective_chat.id)

    await update.message.reply_text("✅ Subscribed successfully")


# ================= DAILY JOB =================

async def daily_job(context: ContextTypes.DEFAULT_TYPE):

    subs = context.application.bot_data.get("subscribers", set())

    if not subs:
        return

    movies = fetch_movies("Hollywood")

    if not movies:
        return

    text = "🔥 Daily Movie Update\n\n"

    for movie in movies:
        text += f"🎬 {movie['Title']} ({movie['Year']})\n"

    for chat_id in subs:

        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            print("Send error:", e)


# ================= MAIN =================

def main():

    if not BOT_TOKEN:
        print("Bot token missing. Cannot start.")
        return

    print("Starting Telegram bot...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # add commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("latest", latest))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("subscribe", subscribe))

    # scheduler
    if app.job_queue:
        app.job_queue.run_repeating(
            daily_job,
            interval=86400,
            first=30
        )

    print("Bot started successfully!")

    app.run_polling()


# ================= RUN =================

if __name__ == "__main__":
    main()