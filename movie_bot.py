import os
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ================= ENV VARIABLES =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OMDB_API = os.environ.get("OMDB_API")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN not found in environment")

if not OMDB_API:
    raise RuntimeError("❌ OMDB_API not found in environment")

# ================= HELPERS =================
def fetch_movies(query="Batman"):
    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&s={query}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
    except Exception:
        return []

    if data.get("Response") == "False":
        return []

    return data.get("Search", [])[:5]


def search_movie(title):
    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&t={title}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
    except Exception:
        return None

    if data.get("Response") == "False":
        return None

    return data


# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Bot is running successfully!*\n\n"
        "🎬 Welcome to Movie Bot\n\n"
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
        text = f"🎬 {movie['Title']} ({movie['Year']})"
        await update.message.reply_text(text)


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search movie_name")
        return

    movie = search_movie(" ".join(context.args))

    if not movie:
        await update.message.reply_text("❌ Movie not found.")
        return

    text = (
        f"🎬 {movie['Title']}\n"
        f"⭐ IMDb: {movie.get('imdbRating')}\n"
        f"🗓 Year: {movie.get('Year')}\n\n"
        f"{movie.get('Plot')}"
    )

    await update.message.reply_text(text)


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = context.application.bot_data.setdefault("subscribers", set())
    subs.add(update.effective_chat.id)
    await update.message.reply_text("✅ Subscribed!")


# ================= DAILY JOB =================
async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    subs = context.application.bot_data.get("subscribers", set())
    if not subs:
        return

    movies = fetch_movies("Hollywood")
    text = "🔥 *Daily Movie Update*\n\n"
    for m in movies:
        text += f"🎬 {m['Title']} ({m['Year']})\n"

    for chat_id in subs:
        await context.application.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown"
        )


# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("latest", latest))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("subscribe", subscribe))

    app.job_queue.run_repeating(daily_job, interval=86400, first=10)

    print("🤖 Bot is running... (waiting for Telegram updates)")
    app.run_polling()


if __name__ == "__main__":
    main()