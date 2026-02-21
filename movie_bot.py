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
OMDB_API = os.environ.get("fbb246db")  # Your OMDb API key

if not BOT_TOKEN:
    print("Error: BOT_TOKEN not found. Bot will not start.")
    exit(1)

if not OMDB_API:
    print("Error: OMDB_API not found. Bot will not start.")
    exit(1)

# ---------------- HELPERS ----------------
def fetch_movies(query="Batman"):
    """
    Fetch top 5 movies based on a search query.
    OMDb doesn't provide latest movies endpoint, so we simulate with a keyword.
    """
    url = f"http://www.omdbapi.com/?apikey={OMDB_API}&s={query}"
    res = requests.get(url)

    if res.status_code != 200:
        return []

    data = res.json()
    if data.get("Response") == "False":
        return []

    return data.get("Search", [])[:5]  # top 5 results


def search_movie(title):
    """
    Search a single movie by exact title
    """
    url = f"http://www.omdbapi.com/?apikey={OMDB_API}&t={title}"
    res = requests.get(url)

    if res.status_code != 200:
        return None

    data = res.json()
    if data.get("Response") == "False":
        return None

    return data

# ---------------- COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Welcome to Movie Bot!\n"
        "Use /latest to see top movies or /search <movie name> to search a movie."
    )

async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movies = fetch_movies()
    if not movies:
        await update.message.reply_text("Error fetching movies.")
        return

    for movie in movies:
        caption = (
            f"🎬 {movie.get('Title')}\n"
            f"⭐ IMDb Rating: {movie.get('imdbID','N/A')}\n"
            f"🗓 Year: {movie.get('Year')}\n"
        )

        poster = movie.get("Poster")
        if poster and poster != "N/A":
            await update.message.reply_photo(
                photo=poster,
                caption=caption
            )
        else:
            await update.message.reply_text(caption)


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search movie_name")
        return

    query = " ".join(context.args)
    movie = search_movie(query)

    if not movie:
        await update.message.reply_text("Movie not found.")
        return

    caption = (
        f"🎬 {movie.get('Title')}\n"
        f"⭐ IMDb Rating: {movie.get('imdbRating','N/A')}\n"
        f"🗓 Year: {movie.get('Year')}\n\n"
        f"{movie.get('Plot','No description available')[:400]}..."
    )

    poster = movie.get("Poster")
    if poster and poster != "N/A":
        await update.message.reply_photo(
            photo=poster,
            caption=caption
        )
    else:
        await update.message.reply_text(caption)


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers = context.application.bot_data.setdefault("subs", [])

    if chat_id not in subscribers:
        subscribers.append(chat_id)

    await update.message.reply_text("Subscribed to daily updates.")


# ---------------- DAILY AUTO UPDATE ----------------
def send_daily(app):
    subscribers = app.bot_data.get("subs", [])
    movies = fetch_movies("Batman")  # Default daily keyword

    if not movies:
        return

    text = "🔥 Daily Movie Update:\n\n"
    for movie in movies:
        text += f"{movie.get('Title')} ⭐ IMDb: {movie.get('imdbID','N/A')}\n"

    for chat_id in subscribers:
        app.bot.send_message(chat_id=chat_id, text=text)


# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("latest", latest))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("subscribe", subscribe))

    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: send_daily(app), "interval", hours=24)
    scheduler.start()

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()

