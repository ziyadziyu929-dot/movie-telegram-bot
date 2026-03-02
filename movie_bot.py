import os
import requests
import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# CONFIG
BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

TMDB_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

logging.basicConfig(level=logging.INFO)

# LANGUAGE MAP
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

# DETECT LANGUAGE
def detect_language(text):
    text = text.lower()
    for lang in LANG_MAP:
        if lang in text:
            return lang
    return None

# CLEAN NAME
def clean_query(text):
    text = text.lower()
    for lang in LANG_MAP:
        text = text.replace(lang, "")
    return text.strip()

# SEARCH ALL PARTS
def search_all_movies(query):

    lang = detect_language(query)
    clean_name = clean_query(query)

    url = f"{TMDB_BASE}/search/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "query": clean_name,
    }

    res = requests.get(url, params=params)
    data = res.json()

    if not data.get("results"):
        return []

    results = data["results"]

    # Filter language if provided
    if lang:
        code = LANG_MAP[lang]
        results = [m for m in results if m["original_language"] == code]

    # Sort by rating
    results.sort(key=lambda x: x.get("vote_average", 0), reverse=True)

    return results[:5]  # show top 5 parts


# POSTER
def get_poster(path):
    if path:
        return IMAGE_BASE + path
    return None


# OTT
def get_ott(movie_id):

    url = f"{TMDB_BASE}/movie/{movie_id}/watch/providers"

    params = {"api_key": TMDB_API_KEY}

    res = requests.get(url, params=params)
    data = res.json()

    try:
        return data["results"]["IN"]["flatrate"][0]["provider_name"]
    except:
        return "Not available"


# TRAILER
def get_trailer(title):

    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "key": YOUTUBE_API_KEY,
        "q": title + " official trailer",
        "part": "snippet",
        "maxResults": 1,
        "type": "video"
    }

    res = requests.get(url, params=params)
    data = res.json()

    try:
        vid = data["items"][0]["id"]["videoId"]
        return f"https://youtu.be/{vid}"
    except:
        return "Not available"


# FORMAT MOVIE
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


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🎬 Movie Bot Ready\n\nSend movie name\nExample:\nDrishyam\nDrishyam malayalam"
    )


# SEARCH HANDLER
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.message.text

    await update.message.reply_text("🔍 Searching all parts...")

    movies = search_all_movies(query)

    if not movies:

        await update.message.reply_text("❌ Movie not found")
        return

    for movie in movies:

        msg, poster = format_movie(movie)

        try:

            if poster:

                await update.message.reply_photo(
                    photo=poster,
                    caption=msg
                )

            else:

                await update.message.reply_text(msg)

        except:

            await update.message.reply_text(msg)


# MAIN
def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

    print("Bot running...")

    app.run_polling()


if __name__ == "__main__":
    main()