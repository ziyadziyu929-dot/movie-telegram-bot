import os
import requests
import random
from datetime import datetime, timedelta

from telegram import ReplyKeyboardMarkup, Update, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # for auto notification

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

if not TMDB_API_KEY:
    raise ValueError("TMDB_API_KEY missing")

# ================= LANGUAGES =================

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
    ["🎬 Upcoming Movies"],
    ["🎲 Random Latest Movies"],
    ["🇮🇳 Malayalam", "🇮🇳 Tamil"],
    ["🇮🇳 Hindi", "🇬🇧 English"],
    ["🇮🇳 Telugu", "🇮🇳 Kannada"],
    ["🇰🇷 Korean", "🇯🇵 Japanese"],
]

reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🎬 Advanced Movie Bot Ready!\n\n"
        "Features:\n"
        "• Poster Image\n"
        "• OTT info\n"
        "• Latest Movies\n"
        "• Upcoming Movies\n"
        "• Auto Notifications\n\n"
        "Try:\n"
        "Drishyam Malayalam",
        reply_markup=reply_markup
    )

# ================= SEARCH =================

def search_movie(query, lang=None):

    url = f"{BASE_URL}/search/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "query": query
    }

    res = requests.get(url, params=params).json()

    results = res.get("results", [])

    if lang:
        results = [m for m in results if m["original_language"] == lang]

    return results[:5]

# ================= DETAILS =================

def get_details(movie_id):

    url = f"{BASE_URL}/movie/{movie_id}"

    params = {
        "api_key": TMDB_API_KEY,
        "append_to_response": "videos,watch/providers"
    }

    return requests.get(url, params=params).json()

# ================= TRAILER =================

def get_trailer(details):

    videos = details.get("videos", {}).get("results", [])

    for v in videos:
        if v["site"] == "YouTube":
            return f"https://youtube.com/watch?v={v['key']}"

    return "Not available"

# ================= OTT =================

def get_ott(details):

    providers = details.get("watch/providers", {})

    india = providers.get("results", {}).get("IN")

    if not india:
        return "Not available"

    if "flatrate" in india:
        return india["flatrate"][0]["provider_name"]

    return "Not available"

# ================= FORMAT =================

def format_caption(details):

    title = details.get("title")

    lang = details.get("original_language", "").upper()

    release = details.get("release_date")

    rating = details.get("vote_average")

    overview = details.get("overview")

    trailer = get_trailer(details)

    ott = get_ott(details)

    caption = (
        f"🎬 {title}\n\n"
        f"🌐 Language: {lang}\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {release}\n"
        f"📺 OTT: {ott}\n\n"
        f"📝 {overview}\n\n"
        f"▶ Trailer:\n{trailer}"
    )

    return caption

# ================= SEND MOVIE =================

async def send_movie(update, context, movie_id):

    details = get_details(movie_id)

    caption = format_caption(details)

    poster = details.get("poster_path")

    if poster:

        image = IMAGE_BASE + poster

        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=image,
            caption=caption
        )

    else:

        await update.message.reply_text(caption)

# ================= LATEST =================

async def send_latest(update, context, lang=None):

    url = f"{BASE_URL}/discover/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "release_date.desc",
        "vote_count.gte": 10
    }

    if lang:
        params["with_original_language"] = lang

    res = requests.get(url, params=params).json()

    for movie in res.get("results", [])[:5]:

        await send_movie(update, context, movie["id"])

# ================= UPCOMING =================

async def send_upcoming(update, context):

    url = f"{BASE_URL}/movie/upcoming"

    params = {"api_key": TMDB_API_KEY}

    res = requests.get(url, params=params).json()

    for movie in res.get("results", [])[:5]:

        await send_movie(update, context, movie["id"])

# ================= RANDOM =================

async def send_random(update, context):

    url = f"{BASE_URL}/discover/movie"

    params = {"api_key": TMDB_API_KEY}

    res = requests.get(url, params=params).json()

    movies = res.get("results", [])

    sample = random.sample(movies, min(5, len(movies)))

    for movie in sample:

        await send_movie(update, context, movie["id"])

# ================= AUTO NOTIFY =================

async def auto_notify(context: ContextTypes.DEFAULT_TYPE):

    if not CHANNEL_ID:
        return

    url = f"{BASE_URL}/movie/upcoming"

    params = {"api_key": TMDB_API_KEY}

    res = requests.get(url, params=params).json()

    movie = res.get("results", [])[0]

    if not movie:
        return

    details = get_details(movie["id"])

    caption = "🔥 New Upcoming Movie!\n\n" + format_caption(details)

    poster = details.get("poster_path")

    if poster:

        await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=IMAGE_BASE + poster,
            caption=caption
        )

# ================= MESSAGE HANDLER =================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.lower()

    if "latest" in text:

        await send_latest(update, context)

        return

    if "upcoming" in text:

        await send_upcoming(update, context)

        return

    if "random" in text:

        await send_random(update, context)

        return

    lang = None

    for name, code in LANGUAGES:

        if name.lower() in text:
            lang = code
            text = text.replace(name.lower(), "").strip()

    movies = search_movie(text, lang)

    if not movies:

        await update.message.reply_text("Movie not found")

        return

    for movie in movies:

        await send_movie(update, context, movie["id"])

# ================= MAIN =================

def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.TEXT, handle))

    # Auto notification every 24 hours
    app.job_queue.run_repeating(
        auto_notify,
        interval=86400,
        first=10
    )

    print("Bot running...")

    app.run_polling()

# ================= RUN =================

if __name__ == "__main__":
    main()