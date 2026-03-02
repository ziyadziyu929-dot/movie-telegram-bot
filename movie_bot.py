import os
import requests
import logging
import random

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
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
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

TMDB_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

logging.basicConfig(level=logging.INFO)

# ================= LANGUAGE MAP =================

LANG_MAP = {
    "english": "en",
    "malayalam": "ml",
    "tamil": "ta",
    "korean": "ko",
    "hindi": "hi",
    "telugu": "te",
    "kannada": "kn",
    "japanese": "ja",
}

# ================= MAIN MENU =================

main_keyboard = ReplyKeyboardMarkup(
    [
        ["🔥 Latest Movies", "🎲 Random Movies"],
        ["🌎 All Movies"]
    ],
    resize_keyboard=True
)

# ================= LANGUAGE MENU =================

language_keyboard = ReplyKeyboardMarkup(
    [
        ["English", "Malayalam"],
        ["Tamil", "Korean"],
        ["Hindi", "Telugu"],
        ["Kannada", "Japanese"],
        ["⬅ Back"]
    ],
    resize_keyboard=True
)

# ================= SEARCH MOVIE =================

def search_movie(query):

    url = f"{TMDB_BASE}/search/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
    }

    response = requests.get(url, params=params)
    data = response.json()

    if not data.get("results"):
        return None

    results = data["results"]

    # priority highest rating
    results.sort(key=lambda x: x.get("vote_average", 0), reverse=True)

    return results[0]


# ================= GET LATEST MOVIES =================

def get_latest_movies(lang_code=None):

    url = f"{TMDB_BASE}/discover/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "vote_average.desc",
        "vote_count.gte": 100,
        "page": random.randint(1, 5),
    }

    if lang_code:
        params["with_original_language"] = lang_code

    response = requests.get(url, params=params)
    data = response.json()

    if data.get("results"):
        return random.choice(data["results"])

    return None


# ================= RANDOM MOVIE =================

def get_random_movie():

    url = f"{TMDB_BASE}/discover/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "page": random.randint(1, 50),
    }

    response = requests.get(url, params=params)
    data = response.json()

    if data.get("results"):
        return random.choice(data["results"])

    return None


# ================= POSTER =================

def get_poster(path):

    if path:
        return IMAGE_BASE + path

    return None


# ================= OTT =================

def get_ott(movie_id):

    url = f"{TMDB_BASE}/movie/{movie_id}/watch/providers"

    params = {"api_key": TMDB_API_KEY}

    response = requests.get(url, params=params)
    data = response.json()

    try:
        return data["results"]["IN"]["flatrate"][0]["provider_name"]
    except:
        return "Not available"


# ================= TRAILER =================

def get_trailer(title):

    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "key": YOUTUBE_API_KEY,
        "q": title + " official trailer",
        "part": "snippet",
        "maxResults": 1,
        "type": "video"
    }

    response = requests.get(url, params=params)
    data = response.json()

    try:
        vid = data["items"][0]["id"]["videoId"]
        return f"https://youtu.be/{vid}"
    except:
        return "Not available"


# ================= FORMAT =================

def format_movie(movie):

    title = movie.get("title", "Unknown")
    release = movie.get("release_date", "Unknown")
    rating = movie.get("vote_average", "N/A")
    overview = movie.get("overview", "No description")
    lang = movie.get("original_language", "").upper()

    poster = get_poster(movie.get("poster_path"))
    ott = get_ott(movie.get("id"))
    trailer = get_trailer(title)

    msg = (
        f"🎬 {title}\n"
        f"🌎 Language: {lang}\n\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {release}\n"
        f"📺 OTT: {ott}\n\n"
        f"📝 {overview[:200]}...\n\n"
        f"🎞 Trailer:\n{trailer}"
    )

    return msg, poster


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🎬 Movie Bot Ready!\n\n"
        "Search movie name or use buttons",
        reply_markup=main_keyboard
    )


# ================= HANDLER =================

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.lower()

    # Latest button
    if "latest movies" in text:

        await update.message.reply_text(
            "Select Language",
            reply_markup=language_keyboard
        )
        return


    # Language selected
    if text in LANG_MAP:

        await update.message.reply_text("🔍 Finding best rated movie...")

        movie = get_latest_movies(LANG_MAP[text])

        if movie:
            msg, poster = format_movie(movie)

            if poster:
                await update.message.reply_photo(photo=poster, caption=msg)
            else:
                await update.message.reply_text(msg)

        return


    # Random movie
    if "random movies" in text:

        await update.message.reply_text("🎲 Finding random movie...")

        movie = get_random_movie()

        msg, poster = format_movie(movie)

        if poster:
            await update.message.reply_photo(photo=poster, caption=msg)
        else:
            await update.message.reply_text(msg)

        return


    # All movies
    if "all movies" in text:

        await update.message.reply_text("🌎 Finding best movie...")

        movie = get_latest_movies()

        msg, poster = format_movie(movie)

        if poster:
            await update.message.reply_photo(photo=poster, caption=msg)
        else:
            await update.message.reply_text(msg)

        return


    # Back button
    if "back" in text:

        await update.message.reply_text(
            "Main Menu",
            reply_markup=main_keyboard
        )
        return


    # SEARCH MOVIE
    await update.message.reply_text("🔍 Searching...")

    movie = search_movie(text)

    if not movie:
        await update.message.reply_text("❌ Movie not found")
        return

    msg, poster = format_movie(movie)

    if poster:
        await update.message.reply_photo(photo=poster, caption=msg)
    else:
        await update.message.reply_text(msg)


# ================= MAIN =================

def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handler)
    )

    print("Bot running...")

    app.run_polling()


# ================= RUN =================

if __name__ == "__main__":
    main()