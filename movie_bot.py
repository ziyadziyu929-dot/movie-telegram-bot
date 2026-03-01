import os
import logging
import random
import requests
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ================= LOGGING =================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Safe convert GROUP_ID
try:
    GROUP_ID = int(CHANNEL_ID.strip())
except (TypeError, ValueError, AttributeError):
    logging.error(f"Invalid CHANNEL_ID: {CHANNEL_ID}")
    GROUP_ID = None

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# prevent duplicates
posted_movies = set()

# ================= FUNCTIONS =================

def get_latest_movies():
    url = f"{BASE_URL}/discover/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "release_date.desc",
        "vote_count.gte": 50,
        "page": random.randint(1, 5),
    }

    res = requests.get(url, params=params)
    data = res.json()

    return data.get("results", [])


def get_trailer(movie_name):
    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "part": "snippet",
        "q": f"{movie_name} official trailer",
        "key": YOUTUBE_API_KEY,
        "maxResults": 1,
        "type": "video"
    }

    res = requests.get(url, params=params)
    data = res.json()

    try:
        video_id = data["items"][0]["id"]["videoId"]
        return f"https://youtu.be/{video_id}"
    except:
        return "Trailer not available"


def format_movie(movie):

    title = movie.get("title", "Unknown")
    rating = movie.get("vote_average", "N/A")
    date = movie.get("release_date", "N/A")
    overview = movie.get("overview", "No description")

    trailer = get_trailer(title)

    caption = (
        f"🎬 {title}\n\n"
        f"⭐ Rating: {rating}\n"
        f"📅 Release: {date}\n\n"
        f"📝 {overview[:300]}...\n\n"
        f"▶ Trailer: {trailer}"
    )

    poster = movie.get("poster_path")

    if poster:
        poster_url = IMAGE_BASE + poster
    else:
        poster_url = None

    return caption, poster_url, title


# ================= COMMAND =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Movie Bot Running!\n\n"
        "Auto posts latest movies every 30 minutes."
    )


# ================= AUTO POST =================

async def auto_post(context: ContextTypes.DEFAULT_TYPE):

    if GROUP_ID is None:
        logging.error("GROUP_ID is None")
        return

    movies = get_latest_movies()

    for movie in movies:

        movie_id = movie["id"]

        if movie_id in posted_movies:
            continue

        caption, poster, title = format_movie(movie)

        try:

            if poster:
                await context.bot.send_photo(
                    chat_id=GROUP_ID,
                    photo=poster,
                    caption=caption
                )
            else:
                await context.bot.send_message(
                    chat_id=GROUP_ID,
                    text=caption
                )

            posted_movies.add(movie_id)

            logging.info(f"Posted: {title}")

            break

        except Exception as e:
            logging.error(f"Post error: {e}")


# ================= MAIN =================

def main():

    if not BOT_TOKEN:
        logging.error("BOT_TOKEN missing")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # auto post every 30 minutes
    app.job_queue.run_repeating(
        auto_post,
        interval=1800,
        first=10
    )

    logging.info("Bot started")

    app.run_polling()


if __name__ == "__main__":
    main()