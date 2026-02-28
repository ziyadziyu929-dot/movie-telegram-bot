import os
import requests
import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ================= ENV =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OMDB_API = os.getenv("OMDB_API")

# ================= HELPERS =================

def fetch_latest_movies():
    """Fetch latest movies from current year"""
    if not OMDB_API:
        return []

    year = datetime.datetime.now().year

    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&s=movie&y={year}&type=movie"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()
    except:
        return []

    if data.get("Response") == "False":
        return []

    return data.get("Search", [])[:5]


def get_movie_details(imdb_id):
    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&i={imdb_id}"

    try:
        res = requests.get(url, timeout=10)
        return res.json()
    except:
        return None


# ================= COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [InlineKeyboardButton("🔥 Latest Movies", callback_data="latest")],
        [InlineKeyboardButton("🔎 Search Movie", callback_data="search")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎬 Movie Bot Ready!\n\nClick button below:",
        reply_markup=reply_markup
    )


async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):

    movies = fetch_latest_movies()

    if not movies:
        await update.message.reply_text("❌ Cannot fetch latest movies")
        return

    for movie in movies:

        details = get_movie_details(movie["imdbID"])

        if not details:
            continue

        poster = details.get("Poster")
        title = details.get("Title")
        year = details.get("Year")
        rating = details.get("imdbRating")
        plot = details.get("Plot")

        text = (
            f"🎬 {title} ({year})\n"
            f"⭐ IMDb: {rating}\n\n"
            f"{plot}"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "View on IMDb",
                    url=f"https://www.imdb.com/title/{movie['imdbID']}/"
                )
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        if poster and poster != "N/A":

            await update.message.reply_photo(
                photo=poster,
                caption=text,
                reply_markup=reply_markup
            )

        else:

            await update.message.reply_text(
                text=text,
                reply_markup=reply_markup
            )


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):

    subs = context.application.bot_data.setdefault("subscribers", set())

    subs.add(update.effective_chat.id)

    await update.message.reply_text(
        "✅ Subscribed!\nYou will receive daily latest movies at 9:00 AM"
    )


# ================= DAILY JOB =================

async def daily_job(context: ContextTypes.DEFAULT_TYPE):

    subs = context.application.bot_data.get("subscribers", set())

    if not subs:
        return

    movies = fetch_latest_movies()

    for chat_id in subs:

        for movie in movies:

            details = get_movie_details(movie["imdbID"])

            if not details:
                continue

            poster = details.get("Poster")

            text = (
                f"🔥 Latest Movie\n\n"
                f"🎬 {details.get('Title')} ({details.get('Year')})\n"
                f"⭐ {details.get('imdbRating')}\n\n"
                f"{details.get('Plot')}"
            )

            try:

                if poster and poster != "N/A":

                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=poster,
                        caption=text
                    )

                else:

                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=text
                    )

            except Exception as e:
                print(e)


# ================= MAIN =================

def main():

    if not BOT_TOKEN:
        print("BOT_TOKEN missing")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("latest", latest))
    app.add_handler(CommandHandler("subscribe", subscribe))

    # Run daily at 9:00 AM
    app.job_queue.run_daily(
        daily_job,
        time=datetime.time(hour=9, minute=0, second=0)
    )

    print("Bot running...")

    app.run_polling()


# ================= RUN =================

if __name__ == "__main__":
    main()