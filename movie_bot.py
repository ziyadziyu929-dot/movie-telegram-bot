import os
import requests
import asyncio
import random
from datetime import datetime
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

if not TMDB_API_KEY:
    raise ValueError("TMDB_API_KEY missing")

BASE_URL = "https://api.themoviedb.org/3"

# Malayalam priority languages
LANGUAGES = [
    ("Malayalam", "ml"),
    ("Tamil", "ta"),
    ("Hindi", "hi"),
    ("English", "en"),
    ("Telugu", "te"),
    ("Kannada", "kn"),
    ("Korean", "ko"),
    ("Japanese", "ja"),
    ("Chinese", "zh"),
]

# ================= KEYBOARD =================

keyboard = [
    ["🔥 Latest Movies"],
    ["🎲 Random Latest Movies"],
    ["🇮🇳 Malayalam", "🇮🇳 Tamil"],
    ["🇮🇳 Hindi", "🇬🇧 English"],
    ["🇰🇷 Korean", "🇯🇵 Japanese"]
]

reply_markup = ReplyKeyboardMarkup(
    keyboard,
    resize_keyboard=True
)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🎬 Movie Bot Ready!\n\n"
        "You can:\n"
        "• Send any movie name\n"
        "• Send movie name + year\n"
        "• Send movie name + language\n\n"
        "Examples:\n"
        "Drishyam\n"
        "Drishyam Malayalam\n"
        "Drishyam 2013\n"
        "Drishyam Part 2 Malayalam\n\n"
        "Malayalam movies supported with HIGH priority"
    )

    await update.message.reply_text(text, reply_markup=reply_markup)

# ================= SEARCH MOVIE =================

def search_movie(query):

    url = f"{BASE_URL}/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": query
    }

    res = requests.get(url, params=params).json()

    if not res.get("results"):
        return None

    return res["results"][0]

# ================= GET DETAILS =================

def get_movie_details(movie_id):

    url = f"{BASE_URL}/movie/{movie_id}"

    params = {
        "api_key": TMDB_API_KEY,
        "append_to_response": "videos"
    }

    return requests.get(url, params=params).json()

# ================= GET TRAILER =================

def get_trailer(videos):

    for v in videos.get("results", []):
        if v["type"] in ["Trailer", "Teaser"]:
            return f"https://youtube.com/watch?v={v['key']}"

    return "Not available"

# ================= FORMAT MOVIE =================

def format_movie(details):

    title = details.get("title")
    release = details.get("release_date", "Unknown")
    rating = details.get("vote_average", "N/A")
    overview = details.get("overview", "No description")

    trailer = get_trailer(details.get("videos", {}))

    text = (
        f"🎬 {title}\n\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {release}\n\n"
        f"📝 {overview}\n\n"
        f"▶ Trailer: {trailer}"
    )

    return text

# ================= MESSAGE HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    # Latest movies
    if text == "🔥 Latest Movies":
        await send_latest(update)
        return

    if text == "🎲 Random Latest Movies":
        await send_random(update)
        return

    # Language buttons
    for lang_name, lang_code in LANGUAGES:
        if lang_name in text:
            await send_latest(update, lang_code)
            return

    # Normal search
    movie = search_movie(text)

    if not movie:
        await update.message.reply_text("Movie not found")
        return

    details = get_movie_details(movie["id"])

    msg = format_movie(details)

    await update.message.reply_text(msg)

# ================= LATEST MOVIES =================

async def send_latest(update, lang=None):

    url = f"{BASE_URL}/discover/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "release_date.desc",
        "vote_count.gte": 50
    }

    if lang:
        params["with_original_language"] = lang

    res = requests.get(url, params=params).json()

    results = res.get("results", [])[:5]

    if not results:
        await update.message.reply_text("No latest movies found")
        return

    for movie in results:
        details = get_movie_details(movie["id"])
        msg = format_movie(details)
        await update.message.reply_text(msg)

# ================= RANDOM MOVIES =================

async def send_random(update):

    url = f"{BASE_URL}/discover/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "release_date.desc"
    }

    res = requests.get(url, params=params).json()

    results = res.get("results", [])

    movies = random.sample(results, min(5, len(results)))

    for movie in movies:
        details = get_movie_details(movie["id"])
        msg = format_movie(details)
        await update.message.reply_text(msg)

# ================= AUTO UPDATE =================

async def auto_update(context: ContextTypes.DEFAULT_TYPE):

    print("Auto update running")

# ================= MAIN =================

async def main():

    print("Starting bot...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))

    app.job_queue.run_repeating(
        auto_update,
        interval=86400,
        first=10
    )

    print("Bot started successfully")

    await app.run_polling()

# ================= RUN =================

if __name__ == "__main__":
    asyncio.run(main())