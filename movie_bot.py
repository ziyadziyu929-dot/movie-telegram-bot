import os
import requests
import re
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"

# LANGUAGE MAP
LANG_MAP = {
    "english": "en",
    "malayalam": "ml",
    "tamil": "ta",
    "hindi": "hi",
    "telugu": "te",
    "korean": "ko",
    "japanese": "ja",
}

# KEYBOARD
main_keyboard = ReplyKeyboardMarkup(
    [
        ["🔥 Latest Movies", "🔜 Upcoming Movies"],
        ["🌎 All Movies"]
    ],
    resize_keyboard=True
)

language_keyboard = ReplyKeyboardMarkup(
    [
        ["English", "Malayalam"],
        ["Tamil", "Hindi"],
        ["Telugu", "Korean"],
        ["Japanese"]
    ],
    resize_keyboard=True
)

# CLEAN QUERY
def extract_query_data(text):

    text_lower = text.lower()

    # detect language
    language = None
    for lang in LANG_MAP:
        if lang in text_lower:
            language = LANG_MAP[lang]
            text_lower = text_lower.replace(lang, "")
            break

    # detect year
    year_match = re.search(r"\b(19|20)\d{2}\b", text_lower)

    year = None
    if year_match:
        year = year_match.group()
        text_lower = text_lower.replace(year, "")

    movie_name = text_lower.strip()

    return movie_name, language, year


# FORMAT MOVIE
def format_movie(movie):

    title = movie.get("title", "Unknown")
    rating = movie.get("vote_average", "N/A")
    release = movie.get("release_date", "Unknown")
    overview = movie.get("overview", "No description")
    language = movie.get("original_language", "").upper()

    poster = movie.get("poster_path")
    poster_url = POSTER_BASE + poster if poster else None

    message = (
        f"🎬 {title}\n"
        f"🌐 Language: {language}\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {release}\n\n"
        f"📝 {overview[:400]}..."
    )

    return message, poster_url


# SEARCH MOVIES WITH PARTS
def search_movies_full(query):

    name, language, year = extract_query_data(query)

    url = f"{TMDB_BASE}/search/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "query": name,
        "include_adult": False,
        "page": 1
    }

    response = requests.get(url, params=params).json()

    results = response.get("results", [])

    if not results:
        return []

    filtered = []

    for movie in results:

        # language filter
        if language and movie.get("original_language") != language:
            continue

        # year filter
        if year:
            release = movie.get("release_date", "")
            if not release.startswith(year):
                continue

        filtered.append(movie)

    # if no filter results use original results
    if not filtered:
        filtered = results

    # SORT BY RELEASE DATE ASC (show all parts in order)
    filtered.sort(
        key=lambda x: x.get("release_date", "")
    )

    return filtered[:10]


# LATEST MOVIES
def get_latest_movies(language=None):

    today = datetime.today().strftime("%Y-%m-%d")

    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "primary_release_date.desc",
        "primary_release_date.lte": today,
        "vote_count.gte": 100,
        "page": 1
    }

    if language:
        params["with_original_language"] = language

    url = f"{TMDB_BASE}/discover/movie"

    res = requests.get(url, params=params).json()

    return res.get("results", [])[:5]


# UPCOMING MOVIES
def get_upcoming_movies(language=None):

    today = datetime.today().strftime("%Y-%m-%d")

    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "primary_release_date.asc",
        "primary_release_date.gte": today,
        "page": 1
    }

    if language:
        params["with_original_language"] = language

    url = f"{TMDB_BASE}/discover/movie"

    res = requests.get(url, params=params).json()

    return res.get("results", [])[:5]


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🎬 Movie Bot Ready\n\nSearch movie name, language, or year\nExample:\nDrishyam malayalam 2013",
        reply_markup=main_keyboard
    )


# HANDLER
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.lower()

    # latest
    if "latest" in text:
        context.user_data["mode"] = "latest"
        await update.message.reply_text("Select Language", reply_markup=language_keyboard)
        return

    # upcoming
    if "upcoming" in text:
        context.user_data["mode"] = "upcoming"
        await update.message.reply_text("Select Language", reply_markup=language_keyboard)
        return

    # language buttons
    if text in LANG_MAP:

        lang_code = LANG_MAP[text]

        mode = context.user_data.get("mode")

        if mode == "upcoming":
            movies = get_upcoming_movies(lang_code)
        else:
            movies = get_latest_movies(lang_code)

        for movie in movies:

            msg, poster = format_movie(movie)

            if poster:
                await update.message.reply_photo(poster, caption=msg)
            else:
                await update.message.reply_text(msg)

        return

    # SEARCH FULL PARTS
    await update.message.reply_text("🔍 Searching all parts...")

    movies = search_movies_full(text)

    if not movies:
        await update.message.reply_text("❌ Movie not found")
        return

    for movie in movies:

        msg, poster = format_movie(movie)

        if poster:
            await update.message.reply_photo(poster, caption=msg)
        else:
            await update.message.reply_text(msg)


# MAIN
def main():

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handler))

    PORT = int(os.environ.get("PORT", 8080))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=os.getenv("WEBHOOK_URL")
    )


if __name__ == "__main__":
    main()