import os
import requests
import logging
import asyncio
from datetime import datetime, timedelta

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

TMDB = "https://api.themoviedb.org/3"
POSTER = "https://image.tmdb.org/t/p/w500"

logging.basicConfig(level=logging.INFO)

DELETE_TIME = 18000  # 5 hours

# ================= AUTO DELETE =================

async def auto_delete(context, chat_id, message_id):
    await asyncio.sleep(DELETE_TIME)
    try:
        await context.bot.delete_message(chat_id, message_id)
    except:
        pass

def schedule_delete(context, message):
    context.application.create_task(
        auto_delete(context, message.chat_id, message.message_id)
    )

# ================= LANGUAGE =================

LANG = {
    "english": "en",
    "malayalam": "ml",
    "tamil": "ta",
    "hindi": "hi",
    "telugu": "te",
    "korean": "ko",
    "japanese": "ja",
}

# ================= MENU =================

main_menu = ReplyKeyboardMarkup(
    [
        ["🔥 Latest Movies", "🔜 Upcoming Movies"],
        ["📺 Series", "🌎 All Movies"]
    ],
    resize_keyboard=True
)

language_menu = ReplyKeyboardMarkup(
    [
        ["English", "Malayalam"],
        ["Tamil", "Hindi"],
        ["Telugu", "Korean"],
        ["Japanese"],
        ["⬅ Back"]
    ],
    resize_keyboard=True
)

# ================= API =================

def api(url, params):
    try:
        r = requests.get(url, params=params, timeout=15)
        return r.json()
    except:
        return {}

# ================= MOVIE FUNCTIONS =================

def latest_movies(language=None):
    today = datetime.today()
    past = today - timedelta(days=30)

    all_movies = []

    for page in range(1, 4):
        params = {
            "api_key": TMDB_API_KEY,
            "primary_release_date.lte": today.strftime("%Y-%m-%d"),
            "primary_release_date.gte": past.strftime("%Y-%m-%d"),
            "sort_by": "vote_average.desc",
            "vote_count.gte": 100,
            "region": "IN",
            "page": page
        }

        if language:
            params["with_original_language"] = language

        results = api(f"{TMDB}/discover/movie", params).get("results", [])
        all_movies.extend(results)

    unique = {m["id"]: m for m in all_movies}
    final = list(unique.values())

    final.sort(
        key=lambda x: (x.get("vote_average", 0), x.get("release_date", "")),
        reverse=True
    )

    return final


def upcoming_movies(language=None):
    all_movies = []

    for page in range(1, 3):
        params = {
            "api_key": TMDB_API_KEY,
            "primary_release_date.gte": datetime.today().strftime("%Y-%m-%d"),
            "sort_by": "primary_release_date.asc",
            "region": "IN",
            "page": page
        }

        if language:
            params["with_original_language"] = language

        results = api(f"{TMDB}/discover/movie", params).get("results", [])
        all_movies.extend(results)

    return all_movies


def latest_series():
    all_series = []

    for page in range(1, 3):
        params = {
            "api_key": TMDB_API_KEY,
            "sort_by": "first_air_date.desc",
            "page": page
        }

        results = api(f"{TMDB}/discover/tv", params).get("results", [])
        all_series.extend(results)

    return all_series


def smart_search(query):
    params = {"api_key": TMDB_API_KEY, "query": query}
    movies = api(f"{TMDB}/search/movie", params).get("results", [])
    tv = api(f"{TMDB}/search/tv", params).get("results", [])
    return movies + tv

# ================= FORMAT =================

def format_movie(movie):
    title = movie.get("title") or movie.get("name")
    rating = movie.get("vote_average", "N/A")
    date = movie.get("release_date") or movie.get("first_air_date") or "N/A"
    overview = movie.get("overview", "No description")
    poster = movie.get("poster_path")
    poster_url = POSTER + poster if poster else None

    text = (
        f"🎬 {title}\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {date}\n\n"
        f"{overview[:300]}..."
    )

    return text, poster_url

# ================= SEND MOVIES =================

async def send_movies(msg, context, movies, page=1):

    if not movies:
        sent = await msg.reply_text("❌ No movies found")
        schedule_delete(context, sent)
        return

    per_page = 5
    start = (page - 1) * per_page
    end = start + per_page
    chunk = movies[start:end]

    for movie in chunk:
        text, poster = format_movie(movie)

        if poster:
            sent = await msg.reply_photo(poster, caption=text)
        else:
            sent = await msg.reply_text(text)

        schedule_delete(context, sent)

    if len(movies) > end:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Next ▶", callback_data=f"page_{page+1}")]]
        )
        sent = await msg.reply_text("Next page:", reply_markup=keyboard)
        schedule_delete(context, sent)

    context.user_data["movies"] = movies

# ================= CALLBACK =================

async def button_callback(update, context):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("_")[1])
    movies = context.user_data.get("movies", [])
    await send_movies(query.message, context, movies, page)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sent = await update.message.reply_text(
        "🎬 Movie Bot Ready\n\nType movie name like:\nKGF 2 Malayalam",
        reply_markup=main_menu
    )
    schedule_delete(context, sent)

# ================= HANDLE =================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    schedule_delete(context, update.message)

    text = update.message.text.lower()

    if text == "⬅ back":
        sent = await update.message.reply_text("Main menu", reply_markup=main_menu)
        schedule_delete(context, sent)
        return

    if "latest" in text:
        context.user_data["mode"] = "latest"
        sent = await update.message.reply_text("Choose language", reply_markup=language_menu)
        schedule_delete(context, sent)
        return

    if "upcoming" in text:
        context.user_data["mode"] = "upcoming"
        sent = await update.message.reply_text("Choose language", reply_markup=language_menu)
        schedule_delete(context, sent)
        return

    if text in LANG:
        mode = context.user_data.get("mode", "latest")
        movies = upcoming_movies(LANG[text]) if mode == "upcoming" else latest_movies(LANG[text])
        await send_movies(update.message, context, movies)
        return

    if "series" in text:
        await send_movies(update.message, context, latest_series())
        return

    if "all movies" in text:
        await send_movies(update.message, context, latest_movies())
        return

    movies = smart_search(text)
    await send_movies(update.message, context, movies)

# ================= MAIN =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()