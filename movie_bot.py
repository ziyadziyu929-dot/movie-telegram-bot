import os
import requests
import logging

from telegram import Update
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

# Malayalam priority
LANGUAGE = "ml-IN"
REGION = "IN"

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ================= CHECK TOKENS =================

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

if not TMDB_API_KEY:
    raise ValueError("TMDB_API_KEY missing")

if not YOUTUBE_API_KEY:
    raise ValueError("YOUTUBE_API_KEY missing")

# ================= SEARCH MOVIE =================

def search_movie(name):

    url = f"{TMDB_BASE}/search/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "query": name,
        "language": LANGUAGE,
        "region": REGION,
    }

    response = requests.get(url, params=params)
    data = response.json()

    if data.get("results"):
        return data["results"][0]

    return None


# ================= POSTER =================

def get_poster(path):

    if path:
        return IMAGE_BASE + path

    return None


# ================= OTT PROVIDER =================

def get_ott(movie_id):

    url = f"{TMDB_BASE}/movie/{movie_id}/watch/providers"

    params = {
        "api_key": TMDB_API_KEY
    }

    response = requests.get(url, params=params)
    data = response.json()

    try:
        return data["results"]["IN"]["flatrate"][0]["provider_name"]
    except:
        return "Not available"


# ================= TRAILER =================

def get_trailer(movie_name):

    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "key": YOUTUBE_API_KEY,
        "q": movie_name + " official trailer",
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


# ================= FORMAT MESSAGE =================

def format_movie(movie):

    title = movie.get("title", "Unknown")
    release = movie.get("release_date", "Unknown")
    rating = movie.get("vote_average", "N/A")
    overview = movie.get("overview", "No description")

    poster = get_poster(movie.get("poster_path"))
    ott = get_ott(movie.get("id"))
    trailer = get_trailer(title)

    message = (
        f"🎬 {title}\n\n"
        f"📅 Release Date: {release}\n"
        f"⭐ Rating: {rating}\n"
        f"📺 OTT: {ott}\n\n"
        f"📝 {overview[:200]}...\n\n"
        f"🎞 Trailer:\n{trailer}"
    )

    return message, poster


# ================= START COMMAND =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🎬 Movie Bot Ready!\n\n"
        "Send any movie name.\n\n"
        "Example:\n"
        "Premalu"
    )


# ================= MESSAGE HANDLER =================

async def movie_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    movie_name = update.message.text

    await update.message.reply_text("🔍 Searching...")

    movie = search_movie(movie_name)

    if not movie:

        await update.message.reply_text("❌ Movie not found")
        return

    message, poster = format_movie(movie)

    try:

        if poster:

            await update.message.reply_photo(
                photo=poster,
                caption=message
            )

        else:

            await update.message.reply_text(message)

    except Exception as e:

        logging.error(e)

        await update.message.reply_text(message)


# ================= MAIN =================

def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, movie_handler)
    )

    logging.info("Bot started successfully")

    app.run_polling()


# ================= START =================

if __name__ == "__main__":
    main()