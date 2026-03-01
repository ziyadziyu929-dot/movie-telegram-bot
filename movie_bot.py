import os
import requests
import asyncio
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
GROUP_ID = int(os.getenv("GROUP_ID"))

TMDB_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
LANG = "ml-IN"

logging.basicConfig(level=logging.INFO)

# ================= SEARCH MOVIE =================

def search_movie(name):

    url = f"{TMDB_BASE}/search/movie"

    params = {
        "api_key": TMDB_API_KEY,
        "query": name,
        "language": LANG,
        "region": "IN"
    }

    res = requests.get(url, params=params).json()

    if res.get("results"):
        return res["results"][0]

    return None


# ================= POSTER =================

def get_poster(path):

    if path:
        return IMAGE_BASE + path

    return None


# ================= OTT =================

def get_ott(movie_id):

    url = f"{TMDB_BASE}/movie/{movie_id}/watch/providers"

    params = {
        "api_key": TMDB_API_KEY
    }

    res = requests.get(url, params=params).json()

    try:
        providers = res["results"]["IN"]["flatrate"]
        return providers[0]["provider_name"]

    except:
        return "Not available"


# ================= TRAILER =================

def get_trailer(name):

    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "key": YOUTUBE_API_KEY,
        "q": name + " official trailer",
        "part": "snippet",
        "maxResults": 1,
        "type": "video"
    }

    res = requests.get(url, params=params).json()

    try:
        video_id = res["items"][0]["id"]["videoId"]
        return f"https://youtu.be/{video_id}"

    except:
        return "Not available"


# ================= FORMAT =================

def format_movie(movie):

    title = movie.get("title", "Unknown")
    date = movie.get("release_date", "Unknown")
    rating = movie.get("vote_average", "N/A")

    poster = get_poster(movie.get("poster_path"))
    ott = get_ott(movie.get("id"))
    trailer = get_trailer(title)

    msg = f"""
🎬 {title}

📅 Release: {date}
⭐ Rating: {rating}

📺 OTT: {ott}

🎞 Trailer:
{trailer}
"""

    return msg, poster


# ================= HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🎬 Movie Bot Ready\n\nSend movie name\nExample:\nPremalu"
    )


async def movie_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    name = update.message.text

    movie = search_movie(name)

    if not movie:

        await update.message.reply_text("❌ Movie not found")

        return

    msg, poster = format_movie(movie)

    if poster:

        await update.message.reply_photo(
            photo=poster,
            caption=msg
        )

    else:

        await update.message.reply_text(msg)


# ================= UPCOMING AUTO POST =================

async def upcoming(context: ContextTypes.DEFAULT_TYPE):

    url = f"{TMDB_BASE}/movie/upcoming"

    params = {
        "api_key": TMDB_API_KEY,
        "language": LANG,
        "region": "IN"
    }

    res = requests.get(url, params=params).json()

    if not res.get("results"):
        return

    movie = res["results"][0]

    msg, poster = format_movie(movie)

    try:

        if poster:

            await context.bot.send_photo(
                chat_id=GROUP_ID,
                photo=poster,
                caption="🔥 Upcoming Movie\n" + msg
            )

        else:

            await context.bot.send_message(
                chat_id=GROUP_ID,
                text="🔥 Upcoming Movie\n" + msg
            )

        logging.info("Upcoming movie posted")

    except Exception as e:

        logging.error(e)


# ================= MAIN =================

async def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, movie_handler))

    # AUTO JOB
    app.job_queue.run_repeating(
        upcoming,
        interval=21600,  # 6 hours
        first=20
    )

    print("Bot running...")

    await app.run_polling()


# ================= START =================

if __name__ == "__main__":
    asyncio.run(main())