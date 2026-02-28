import os
import requests
import random
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

# Malayalam PRIORITY
LANGUAGES = [
    ("Malayalam", "ml"),
    ("Tamil", "ta"),
    ("Hindi", "hi"),
    ("English", "en"),
    ("Telugu", "te"),
    ("Kannada", "kn"),
    ("Korean", "ko"),
    ("Japanese", "ja"),
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
        "Features:\n"
        "• Latest Movies (Malayalam priority)\n"
        "• Random Latest Movies\n"
        "• Search any movie\n"
        "• Trailer link\n\n"
        "Examples:\n"
        "Drishyam\n"
        "Drishyam Malayalam\n"
        "Premalu\n"
        "Lucifer 2019\n"
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

        if v["site"] == "YouTube" and v["type"] in ["Trailer", "Teaser"]:

            return f"https://youtube.com/watch?v={v['key']}"

    return "Not available"

# ================= FORMAT MOVIE =================

def format_movie(details):

    title = details.get("title", "Unknown")

    release = details.get("release_date", "Unknown")

    rating = details.get("vote_average", "N/A")

    overview = details.get("overview", "No description")

    lang = details.get("original_language", "").upper()

    trailer = get_trailer(details.get("videos", {}))

    text = (
        f"🎬 {title}\n\n"
        f"🌐 Language: {lang}\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {release}\n\n"
        f"📝 {overview}\n\n"
        f"▶ Trailer:\n{trailer}"
    )

    return text

# ================= SEND MOVIE =================

async def send_movie(update, movie_id):

    details = get_movie_details(movie_id)

    msg = format_movie(details)

    await update.message.reply_text(msg)

# ================= LATEST MOVIES =================

async def send_latest(update, lang=None):

    url = f"{BASE_URL}/discover/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "release_date.desc",
        "vote_count.gte": 20
    }

    if lang:
        params["with_original_language"] = lang

    res = requests.get(url, params=params).json()

    results = res.get("results", [])

    if not results:
        await update.message.reply_text("No latest movies found")
        return

    count = 0

    for movie in results:

        await send_movie(update, movie["id"])

        count += 1

        if count >= 5:
            break

# ================= RANDOM LATEST =================

async def send_random(update):

    url = f"{BASE_URL}/discover/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "release_date.desc",
        "vote_count.gte": 20
    }

    res = requests.get(url, params=params).json()

    results = res.get("results", [])

    if not results:
        await update.message.reply_text("No movies found")
        return

    movies = random.sample(results, min(5, len(results)))

    for movie in movies:

        await send_movie(update, movie["id"])

# ================= AUTO UPDATE =================

async def auto_update(context: ContextTypes.DEFAULT_TYPE):

    print("Auto update running...")

# ================= MESSAGE HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    # Latest button
    if text == "🔥 Latest Movies":

        await send_latest(update)

        return

    # Random button
    if text == "🎲 Random Latest Movies":

        await send_random(update)

        return

    # Language buttons
    for lang_name, lang_code in LANGUAGES:

        if lang_name in text:

            await send_latest(update, lang_code)

            return

    # Search movie
    movie = search_movie(text)

    if not movie:

        await update.message.reply_text("❌ Movie not found")

        return

    await send_movie(update, movie["id"])

# ================= MAIN =================

def main():

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

    app.run_polling()

# ================= RUN =================

if __name__ == "__main__":

    main()