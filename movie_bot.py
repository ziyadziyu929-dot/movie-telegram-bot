import os
import requests
import logging
import random

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

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

# ================= KEYBOARDS =================

main_keyboard = ReplyKeyboardMarkup(
    [
        ["🔥 Latest Movies", "🎲 Random Movies"],
        ["🌎 All Movies"],
        ["📋 Menu"]
    ],
    resize_keyboard=True
)

language_keyboard = ReplyKeyboardMarkup(
    [
        ["English", "Malayalam"],
        ["Tamil", "Korean"],
        ["Hindi", "Telugu"],
        ["Kannada", "Japanese"],
        ["⬅ Back", "📋 Menu"]
    ],
    resize_keyboard=True
)

# ================= LANGUAGE DETECT =================

def detect_language(text):

    text = text.lower()

    for lang in LANG_MAP:
        if lang in text:
            return lang

    return None


# ================= CLEAN QUERY =================

def clean_query(text):

    text = text.lower()

    for lang in LANG_MAP:
        text = text.replace(lang, "")

    return text.strip()


# ================= SEARCH MOVIE =================

def search_movie(query):

    lang = detect_language(query)
    clean_name = clean_query(query)

    url = f"{TMDB_BASE}/search/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "query": clean_name,
    }

    response = requests.get(url, params=params)
    data = response.json()

    if not data.get("results"):
        return None

    results = data["results"]

    # Filter by language if specified
    if lang:
        code = LANG_MAP[lang]
        filtered = [m for m in results if m.get("original_language") == code]

        if filtered:
            filtered.sort(key=lambda x: x.get("vote_average", 0), reverse=True)
            return filtered[0]

    # Otherwise return highest rated
    results.sort(key=lambda x: x.get("vote_average", 0), reverse=True)
    return results[0]


# ================= LATEST MOVIES =================

def get_latest_movies(lang_code=None):

    url = f"{TMDB_BASE}/discover/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "vote_average.desc",
        "vote_count.gte": 200,
        "page": random.randint(1, 10),
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
        video_id = data["items"][0]["id"]["videoId"]
        return f"https://youtu.be/{video_id}"
    except:
        return "Not available"


# ================= FORMAT MOVIE =================

def format_movie(movie):

    title = movie.get("title", "Unknown")
    rating = movie.get("vote_average", "N/A")
    release = movie.get("release_date", "Unknown")
    overview = movie.get("overview", "No description")
    lang = movie.get("original_language", "").upper()

    poster = get_poster(movie.get("poster_path"))
    ott = get_ott(movie.get("id"))
    trailer = get_trailer(title)

    message = (
        f"🎬 {title}\n"
        f"🌎 Language: {lang}\n\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {release}\n"
        f"📺 OTT: {ott}\n\n"
        f"📝 {overview[:200]}...\n\n"
        f"🎞 Trailer:\n{trailer}"
    )

    return message, poster


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🎬 Movie Bot Ready!\n\nUse Menu below 👇",
        reply_markup=main_keyboard
    )


# ================= MAIN HANDLER =================

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()
    lower = text.lower()

    # MENU
    if lower == "📋 menu":

        await update.message.reply_text(
            "📋 Main Menu",
            reply_markup=main_keyboard
        )
        return


    # BACK
    if lower == "⬅ back":

        await update.message.reply_text(
            "⬅ Back to Main Menu",
            reply_markup=main_keyboard
        )
        return


    # LATEST BUTTON
    if lower == "🔥 latest movies":

        await update.message.reply_text(
            "Select Language",
            reply_markup=language_keyboard
        )
        return


    # LANGUAGE BUTTONS
    if lower in LANG_MAP:

        await update.message.reply_text("🔍 Finding movie...")

        movie = get_latest_movies(LANG_MAP[lower])

        if movie:

            msg, poster = format_movie(movie)

            if poster:
                await update.message.reply_photo(photo=poster, caption=msg)
            else:
                await update.message.reply_text(msg)

        return


    # RANDOM BUTTON
    if lower == "🎲 random movies":

        await update.message.reply_text("🎲 Finding random movie...")

        movie = get_random_movie()

        if movie:

            msg, poster = format_movie(movie)

            if poster:
                await update.message.reply_photo(photo=poster, caption=msg)
            else:
                await update.message.reply_text(msg)

        return


    # ALL MOVIES
    if lower == "🌎 all movies":

        await update.message.reply_text("🌎 Finding movie...")

        movie = get_latest_movies()

        if movie:

            msg, poster = format_movie(movie)

            if poster:
                await update.message.reply_photo(photo=poster, caption=msg)
            else:
                await update.message.reply_text(msg)

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

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN missing")

    if not TMDB_API_KEY:
        raise ValueError("TMDB_API_KEY missing")

    if not YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY missing")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

    print("✅ Bot running...")

    app.run_polling()


# ================= RUN =================

if __name__ == "__main__":
    main()