
import os
import requests
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from apscheduler.schedulers.background import BackgroundScheduler

# ---------------- LOAD ENV ----------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API = os.getenv("8292328042:AAHOXPdEamr_7tC9lvxfkC2wQrqKbJyAoUc")

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/w500"

LANGUAGES = {
    "English": "en-US",
    "Tamil": "ta-IN",
    "Malayalam": "ml-IN",
    "Hindi": "hi-IN"
}

# ---------------- HELPERS ----------------
def fetch_movies(language="en-US"):
    url = f"{BASE_URL}/movie/now_playing?api_key={TMDB_API}&language={language}"
    res = requests.get(url)

    if res.status_code != 200:
        return []

    data = res.json()
    return data.get("results", [])[:5]


def search_movie(query, language="en-US"):
    url = f"{BASE_URL}/search/movie?api_key={TMDB_API}&query={query}&language={language}"
    res = requests.get(url)

    if res.status_code != 200:
        return None

    results = res.json().get("results")
    if not results:
        return None

    return results[0]


# ---------------- COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(name, callback_data=code)]
        for name, code in LANGUAGES.items()
    ]

    await update.message.reply_text(
        "🎬 Select Language:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movies = fetch_movies()
    if not movies:
        await update.message.reply_text("Error fetching movies.")
        return

    for movie in movies:
        caption = (
            f"🎬 {movie['title']}\n"
            f"⭐ Rating: {movie['vote_average']}\n"
            f"🗓 Release: {movie['release_date']}\n\n"
            f"{movie['overview'][:300]}..."
        )

        poster = movie.get("poster_path")
        if poster:
            await update.message.reply_photo(
                photo=f"{IMAGE_URL}{poster}",
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
        f"🎬 {movie['title']}\n"
        f"⭐ Rating: {movie['vote_average']}\n"
        f"🗓 Release: {movie['release_date']}\n\n"
        f"{movie['overview'][:400]}..."
    )

    poster = movie.get("poster_path")
    if poster:
        await update.message.reply_photo(
            photo=f"{IMAGE_URL}{poster}",
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


# ---------------- INLINE BUTTON ----------------
async def language_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    language = query.data
    movies = fetch_movies(language)

    if not movies:
        await query.edit_message_text("Error fetching movies.")
        return

    text = "🔥 Latest Movies:\n\n"
    for movie in movies:
        text += f"{movie['title']} ⭐ {movie['vote_average']}\n"

    await query.edit_message_text(text)


# ---------------- DAILY AUTO UPDATE ----------------
def send_daily(app):
    subscribers = app.bot_data.get("subs", [])
    movies = fetch_movies("en-US")

    if not movies:
        return

    text = "🔥 Daily Movie Update:\n\n"
    for movie in movies:
        text += f"{movie['title']} ⭐ {movie['vote_average']}\n"

    for chat_id in subscribers:
        app.bot.send_message(chat_id=chat_id, text=text)


# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("latest", latest))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CallbackQueryHandler(language_button))

    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: send_daily(app), "interval", hours=24)
    scheduler.start()

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
