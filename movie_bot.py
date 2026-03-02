import os
import requests
import logging

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

# ================= SEARCH MOVIE =================

def detect_language(text):

    text = text.lower()

    for lang in LANG_MAP:
        if lang in text:
            return lang

    return None


def clean_query(text):

    text = text.lower()

    for lang in LANG_MAP:
        text = text.replace(lang, "")

    return text.strip()


def search_movie(query):

    lang = detect_language(query)
    clean_name = clean_query(query)

    url = f"{TMDB_BASE}/search/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "query": clean_name,
    }

    res = requests.get(url, params=params).json()

    if not res.get("results"):
        return None

    results = res["results"]

    # filter language
    if lang:
        code = LANG_MAP[lang]
        results = [m for m in results if m["original_language"] == code]

        if not results:
            return None

    # sort by rating
    results.sort(key=lambda x: x.get("vote_average", 0), reverse=True)

    return results[0]


# ================= GET MULTIPLE MOVIES =================

def get_latest_movies(lang_code=None):

    url = f"{TMDB_BASE}/discover/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "vote_average.desc",
        "vote_count.gte": 200,
        "primary_release_date.gte": "2020-01-01",
        "page": 1
    }

    if lang_code:
        params["with_original_language"] = lang_code

    res = requests.get(url, params=params).json()

    return res.get("results", [])[:5]


# ================= RANDOM =================

def get_random_movie():

    url = f"{TMDB_BASE}/discover/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "page": 5
    }

    res = requests.get(url, params=params).json()

    results = res.get("results", [])

    if results:
        import random
        return random.choice(results)

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

    res = requests.get(url, params=params).json()

    try:
        return res["results"]["IN"]["flatrate"][0]["provider_name"]
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

    res = requests.get(url, params=params).json()

    try:
        vid = res["items"][0]["id"]["videoId"]
        return f"https://youtu.be/{vid}"
    except:
        return "Not available"


# ================= FORMAT =================

def format_movie(movie):

    title = movie.get("title")
    rating = movie.get("vote_average")
    release = movie.get("release_date")
    overview = movie.get("overview")
    lang = movie.get("original_language").upper()

    poster = get_poster(movie.get("poster_path"))
    ott = get_ott(movie.get("id"))
    trailer = get_trailer(title)

    msg = (
        f"🎬 {title}\n"
        f"🌎 Language: {lang}\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {release}\n"
        f"📺 OTT: {ott}\n\n"
        f"🎞 Trailer:\n{trailer}"
    )

    return msg, poster


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🎬 Movie Bot Ready!",
        reply_markup=main_keyboard
    )


# ================= HANDLER =================

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()
    lower = text.lower()


    if lower == "📋 menu":

        await update.message.reply_text(
            "Main Menu",
            reply_markup=main_keyboard
        )
        return


    if lower == "⬅ back":

        await update.message.reply_text(
            "Back to Menu",
            reply_markup=main_keyboard
        )
        return


    if lower == "🔥 latest movies":

        await update.message.reply_text(
            "Select Language",
            reply_markup=language_keyboard
        )
        return


    # LANGUAGE BUTTONS FIXED
    if lower in LANG_MAP:

        await update.message.reply_text("Fetching latest movies...")

        movies = get_latest_movies(LANG_MAP[lower])

        if not movies:

            await update.message.reply_text("No movies found")
            return

        for movie in movies:

            msg, poster = format_movie(movie)

            if poster:
                await update.message.reply_photo(photo=poster, caption=msg)
            else:
                await update.message.reply_text(msg)

        return


    if lower == "🎲 random movies":

        movie = get_random_movie()

        msg, poster = format_movie(movie)

        if poster:
            await update.message.reply_photo(photo=poster, caption=msg)
        else:
            await update.message.reply_text(msg)

        return


    if lower == "🌎 all movies":

        movies = get_latest_movies()

        for movie in movies:

            msg, poster = format_movie(movie)

            if poster:
                await update.message.reply_photo(photo=poster, caption=msg)
            else:
                await update.message.reply_text(msg)

        return


    # SEARCH
    await update.message.reply_text("Searching...")

    movie = search_movie(text)

    if not movie:

        await update.message.reply_text("Movie not found")
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

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

    print("Bot running...")

    app.run_polling()


if __name__ == "__main__":
    main()