import os
import requests
import asyncio
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
    raise RuntimeError("BOT_TOKEN not found")

if not OMDB_API:
    raise RuntimeError("OMDB_API not found")

# ================= HELPERS =================
def fetch_movies(query="Batman"):
    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&s={query}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
    except Exception as e:
        print("Error fetching movies:", e)
        return []

    if data.get("Response") == "False":
        return []

    return data.get("Search", [])[:5]


def search_movie(title):
    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&t={title}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
    except Exception as e:
        print("Error searching movie:", e)
        return None

    if data.get("Response") == "False":
        return None

    return data


# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot is running on Railway!\n\n"
        "/latest – Top movies\n"
        "/search <name> – Movie details\n"
        "/subscribe – Daily updates"
    )


async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movies = fetch_movies()

    if not movies:
        await update.message.reply_text("Unable to fetch movies.")
        return

    for movie in movies:
        await update.message.reply_text(
            f"{movie['Title']} ({movie['Year']})"
        )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search movie_name")
        return

    movie = search_movie(" ".join(context.args))

    if not movie:
        await update.message.reply_text("Movie not found.")
        return

    text = (
        f"{movie['Title']}\n"
        f"IMDb: {movie.get('imdbRating')}\n"
        f"Year: {movie.get('Year')}\n\n"
        f"{movie.get('Plot')}"
    )

    await update.message.reply_text(text)


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = context.application.bot_data.setdefault("subscribers", set())
    subs.add(update.effective_chat.id)
    await update.message.reply_text("Subscribed successfully!")


# ================= DAILY JOB =================
async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    subs = context.application.bot_data.get("subscribers", set())

    if not subs:
        return

    movies = fetch_movies("Hollywood")

    text = "Daily Movie Update\n\n"

    for m in movies:
        text += f"{m['Title']} ({m['Year']})\n"

    for chat_id in subs:
        try:
            await context.bot.send_message(chat_id, text)
        except Exception as e:
            print("Send failed:", e)


# ================= MAIN =================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("latest", latest))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("subscribe", subscribe))

    app.job_queue.run_repeating(daily_job, interval=86400, first=30)

    print("Bot started on Railway")

    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())