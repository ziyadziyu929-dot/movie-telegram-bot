import os
import requests
import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
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
        res = requests.get(url, timeout=15)
        data = res.json()
    except:
        return []

    if data.get("Response") == "False":
        return []

    return data.get("Search", [])[:5]


def get_movie_details(imdb_id):

    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&i={imdb_id}"

    try:
        res = requests.get(url, timeout=15)
        return res.json()
    except:
        return None


# ================= BUTTON HANDLER =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "latest":

        movies = fetch_latest_movies()

        if not movies:
            await query.message.reply_text("❌ Cannot fetch latest movies")
            return

        for movie in movies:

            details = get_movie_details(movie["imdbID"])

            if not details:
                continue

            poster = details.get("Poster")

            text = (
                f"🎬 {details.get('Title')} ({details.get('Year')})\n"
                f"⭐ IMDb: {details.get('imdbRating')}\n\n"
                f"{details.get('Plot')}"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "View on IMDb",
                        url=f"https://www.imdb.com/title/{movie['imdbID']}/"
                    )
                ]
            ]

            markup = InlineKeyboardMarkup(keyboard)

            if poster and poster != "N/A":

                await query.message.reply_photo(
                    photo=poster,
                    caption=text,
                    reply_markup=markup
                )

            else:

                await query.message.reply_text(
                    text=text,
                    reply_markup=markup
                )


# ================= COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [InlineKeyboardButton("🔥 Latest Movies", callback_data="latest")],
        [InlineKeyboardButton("✅ Subscribe Daily", callback_data="subscribe")]
    ]

    markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎬 Movie Bot Ready!\n\nClick below:",
        reply_markup=markup
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

        text = (
            f"🎬 {details.get('Title')} ({details.get('Year')})\n"
            f"⭐ IMDb: {details.get('imdbRating')}\n\n"
            f"{details.get('Plot')}"
        )

        if poster and poster != "N/A":

            await update.message.reply_photo(
                photo=poster,
                caption=text
            )

        else:

            await update.message.reply_text(text)


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):

    subs = context.application.bot_data.setdefault("subs", set())

    subs.add(update.effective_chat.id)

    await update.message.reply_text(
        "✅ Subscribed!\nDaily movies at 9:00 AM IST"
    )


# ================= DAILY JOB =================

async def daily_job(context: ContextTypes.DEFAULT_TYPE):

    subs = context.application.bot_data.get("subs", set())

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
                f"🔥 Daily Latest Movie\n\n"
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

    print("Starting bot...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("latest", latest))
    app.add_handler(CommandHandler("subscribe", subscribe))

    app.add_handler(CallbackQueryHandler(button_handler))

    # 9:00 AM IST = 3:30 AM UTC
    app.job_queue.run_daily(
        daily_job,
        time=datetime.time(hour=3, minute=30)
    )

    print("Bot running successfully!")

    app.run_polling(
        drop_pending_updates=True,
        close_loop=False
    )


# ================= RUN =================

if __name__ == "__main__":
    main()