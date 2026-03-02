import os
import requests
import re
import logging
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"

logging.basicConfig(level=logging.INFO)

# ================= LANGUAGE MAP =================

LANG_MAP = {
    "english": "en",
    "malayalam": "ml",
    "tamil": "ta",
    "hindi": "hi",
    "telugu": "te",
    "korean": "ko",
    "japanese": "ja",
}

# ================= KEYBOARDS =================

main_keyboard = ReplyKeyboardMarkup(
    [
        ["🔥 Latest Movies", "🔜 Upcoming Movies"],
        ["🌎 All Movies"],
    ],
    resize_keyboard=True
)

language_keyboard = ReplyKeyboardMarkup(
    [
        ["English", "Malayalam"],
        ["Tamil", "Hindi"],
        ["Telugu", "Korean"],
        ["Japanese"],
        ["⬅ Back"],
    ],
    resize_keyboard=True
)

# ================= SAFE REQUEST =================

def safe_request(url, params):
    try:
        r = requests.get(url, params=params, timeout=15)
        return r.json()
    except:
        return {}

# ================= EXTRACT QUERY =================

def extract_query(text):

    text = text.lower()

    language = None
    for lang in LANG_MAP:
        if lang in text:
            language = LANG_MAP[lang]
            text = text.replace(lang, "")

    year = None
    match = re.search(r"(19|20)\d{2}", text)
    if match:
        year = match.group()
        text = text.replace(year, "")

    name = text.strip()

    return name, language, year

# ================= GET TRAILER =================

def get_trailer(title):

    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "key": YOUTUBE_API_KEY,
        "q": f"{title} official trailer",
        "part": "snippet",
        "maxResults": 1,
        "type": "video"
    }

    data = safe_request(url, params)

    try:
        video_id = data["items"][0]["id"]["videoId"]
        return f"https://youtu.be/{video_id}"
    except:
        return "Not available"

# ================= GET OTT =================

def get_ott(movie_id):

    url = f"{TMDB_BASE}/movie/{movie_id}/watch/providers"

    params = {"api_key": TMDB_API_KEY}

    data = safe_request(url, params)

    try:
        providers = data["results"]["IN"]["flatrate"]
        return providers[0]["provider_name"]
    except:
        return "Not available"

# ================= FORMAT MOVIE =================

def format_movie(movie):

    title = movie.get("title", "Unknown")
    rating = movie.get("vote_average", "N/A")
    release = movie.get("release_date", "Unknown")
    overview = movie.get("overview", "No description")
    language = movie.get("original_language", "").upper()

    poster = movie.get("poster_path")
    poster_url = POSTER_BASE + poster if poster else None

    ott = get_ott(movie.get("id"))
    trailer = get_trailer(title)

    msg = (
        f"🎬 {title}\n"
        f"🌐 Language: {language}\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {release}\n"
        f"📺 OTT: {ott}\n\n"
        f"📝 {overview[:300]}...\n\n"
        f"🎞 Trailer:\n{trailer}"
    )

    return msg, poster_url

# ================= SEARCH FULL PARTS =================

def search_movies(query):

    name, language, year = extract_query(query)

    url = f"{TMDB_BASE}/search/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "query": name,
        "page": 1,
    }

    data = safe_request(url, params)

    results = data.get("results", [])

    if language:
        results = [m for m in results if m.get("original_language") == language]

    if year:
        results = [m for m in results if m.get("release_date", "").startswith(year)]

    # SORT BY RELEASE DATE → SHOW ALL PARTS ORDER
    results.sort(key=lambda x: x.get("release_date", ""))

    return results[:10]

# ================= LATEST MOVIES =================

def get_latest_movies(language=None):

    today = datetime.today().strftime("%Y-%m-%d")

    params = {
        "api_key": TMDB_API_KEY,
        "primary_release_date.lte": today,
        "sort_by": "vote_average.desc",
        "vote_count.gte": 200,
        "page": 1,
    }

    if language:
        params["with_original_language"] = language

    url = f"{TMDB_BASE}/discover/movie"

    data = safe_request(url, params)

    movies = data.get("results", [])

    # SORT BY RELEASE DATE FIRST THEN RATING
    movies.sort(
        key=lambda x: (
            x.get("release_date", ""),
            x.get("vote_average", 0)
        ),
        reverse=True
    )

    return movies[:6]

# ================= UPCOMING MOVIES =================

def get_upcoming_movies(language=None):

    today = datetime.today().strftime("%Y-%m-%d")

    params = {
        "api_key": TMDB_API_KEY,
        "primary_release_date.gte": today,
        "sort_by": "primary_release_date.asc",
        "page": 1,
    }

    if language:
        params["with_original_language"] = language

    url = f"{TMDB_BASE}/discover/movie"

    data = safe_request(url, params)

    return data.get("results", [])[:6]

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🎬 Movie Bot Ready\n\n"
        "Search movie name, language, year, or part\n"
        "Example:\n"
        "• Batman english\n"
        "• Drishyam malayalam\n"
        "• Pushpa 2021 hindi\n",
        reply_markup=main_keyboard
    )

# ================= SEND MOVIES =================

async def send_movies(update, movies):

    if not movies:
        await update.message.reply_text("❌ No movies found")
        return

    for movie in movies:

        msg, poster = format_movie(movie)

        try:
            if poster:
                await update.message.reply_photo(poster, caption=msg)
            else:
                await update.message.reply_text(msg)
        except:
            continue

# ================= HANDLER =================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.lower()

    # BACK
    if text == "⬅ back":
        await update.message.reply_text("Main Menu", reply_markup=main_keyboard)
        return

    # LATEST BUTTON
    if "latest" in text:
        context.user_data["mode"] = "latest"
        await update.message.reply_text("Select Language", reply_markup=language_keyboard)
        return

    # UPCOMING BUTTON
    if "upcoming" in text:
        context.user_data["mode"] = "upcoming"
        await update.message.reply_text("Select Language", reply_markup=language_keyboard)
        return

    # ALL MOVIES
    if "all movies" in text:
        movies = get_latest_movies()
        await send_movies(update, movies)
        return

    # LANGUAGE SELECT
    if text in LANG_MAP:

        mode = context.user_data.get("mode", "latest")

        if mode == "upcoming":
            movies = get_upcoming_movies(LANG_MAP[text])
        else:
            movies = get_latest_movies(LANG_MAP[text])

        await send_movies(update, movies)
        return

    # SEARCH MOVIES
    await update.message.reply_text("🔍 Searching full movie parts...")

    movies = search_movies(text)

    await send_movies(update, movies)

# ================= MAIN =================

def main():

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("Bot running on Railway...")

    app.run_polling()

# ================= RUN =================

if __name__ == "__main__":
    main()