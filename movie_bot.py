import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GROUP_ID = int(os.getenv("GROUP_ID"))

TMDB_BASE = "https://api.themoviedb.org/3"
LANG = "ml-IN"


# ---------------- MOVIE SEARCH ----------------

def search_movie(name):
    url = f"{TMDB_BASE}/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": name,
        "language": LANG
    }

    res = requests.get(url, params=params).json()

    if res["results"]:
        return res["results"][0]
    return None


# ---------------- POSTER ----------------

def get_poster(path):
    if path:
        return f"https://image.tmdb.org/t/p/w500{path}"
    return None


# ---------------- OTT INFO ----------------

def get_ott(movie_id):
    url = f"{TMDB_BASE}/movie/{movie_id}/watch/providers"
    params = {"api_key": TMDB_API_KEY}

    res = requests.get(url, params=params).json()

    if "results" in res and "IN" in res["results"]:
        providers = res["results"]["IN"].get("flatrate")
        if providers:
            return providers[0]["provider_name"]

    return "Not available"


# ---------------- TRAILER ----------------

def get_trailer(name):
    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "key": YOUTUBE_API_KEY,
        "q": name + " trailer",
        "part": "snippet",
        "maxResults": 1,
        "type": "video"
    }

    res = requests.get(url, params=params).json()

    if res["items"]:
        video_id = res["items"][0]["id"]["videoId"]
        return f"https://youtu.be/{video_id}"

    return None


# ---------------- FORMAT MESSAGE ----------------

def format_movie(movie):

    poster = get_poster(movie["poster_path"])
    ott = get_ott(movie["id"])
    trailer = get_trailer(movie["title"])

    msg = f"""
🎬 {movie['title']}

📅 Release: {movie['release_date']}
⭐ Rating: {movie['vote_average']}

📺 OTT: {ott}

🎞 Trailer:
{trailer}
"""

    return msg, poster


# ---------------- COMMAND HANDLER ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send movie name\nExample:\nPremalu"
    )


# ---------------- MESSAGE HANDLER ----------------

async def movie_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    name = update.message.text

    movie = search_movie(name)

    if not movie:
        await update.message.reply_text("Movie not found")
        return

    msg, poster = format_movie(movie)

    if poster:
        await update.message.reply_photo(poster, caption=msg)
    else:
        await update.message.reply_text(msg)


# ---------------- AUTO UPCOMING MOVIES ----------------

async def upcoming(context: ContextTypes.DEFAULT_TYPE):

    url = f"{TMDB_BASE}/movie/upcoming"

    params = {
        "api_key": TMDB_API_KEY,
        "language": LANG,
        "region": "IN"
    }

    res = requests.get(url, params=params).json()

    if res["results"]:

        movie = res["results"][0]

        msg, poster = format_movie(movie)

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


# ---------------- MAIN ----------------

async def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, movie_handler))

    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        upcoming,
        "interval",
        hours=6,
        args=[app]
    )

    scheduler.start()

    print("Bot running...")

    await app.run_polling()


# ---------------- START ----------------

import asyncio
asyncio.run(main())