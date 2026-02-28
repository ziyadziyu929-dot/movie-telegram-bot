import os
import requests
import datetime
from zoneinfo import ZoneInfo

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
    MessageHandler,
    filters,
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OMDB_API = os.getenv("OMDB_API")

IST = ZoneInfo("Asia/Kolkata")

# ================= HELPERS =================

def fetch_latest_movies():
    """Fetch latest movies from current year"""

    if not OMDB_API:
        print("OMDB_API missing")
        return []

    year = datetime.datetime.now().year

    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&s=movie&y={year}&type=movie"

    try:
        res = requests.get(url, timeout=15)
        data = res.json()
    except Exception as e:
        print("Fetch error:", e)
        return []

    if data.get("Response") == "False":
        print(data.get("Error"))
        return []

    return data.get("Search", [])[:5]


def get_movie_details(imdb_id):

    if not OMDB_API:
        return None

    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&i={imdb_id}"

    try:
        res = requests.get(url, timeout=15)
        return res.json()
    except Exception as e:
        print("Details error:", e)
        return None


def search_movie_by_name(name):

    if not OMDB_API:
        return None

    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&t={name}"

    try:
        res = requests.get(url, timeout=15)
        data = res.json()

        if data.get("Response") == "False":
            return None

        return data

    except Exception as e:
        print("Search error:", e)
        return None


# ================= BUTTON HANDLER =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if "subs" not in context.application.bot_data:
        context.application.bot_data["subs"] = set()

    # Latest button
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

            keyboard = [[
                InlineKeyboardButton(
                    "View on IMDb",
                    url=f"https://www.imdb.com/title/{movie['imdbID']}/"
                )
            ]]

            markup = InlineKeyboardMarkup(keyboard)

            try:

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

            except Exception as e:
                print(e)

    # Subscribe button
    elif query.data == "subscribe":

        chat_id = query.message.chat_id

        context.application.bot_data["subs"].add(chat_id)

        await query.message.reply_text(
            "✅ Subscribed!\nDaily movies at 9:00 AM IST"
        )


# ================= COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [InlineKeyboardButton("🔥 Latest Movies", callback_data="latest")],
        [InlineKeyboardButton("✅ Subscribe Daily", callback_data="subscribe")]
    ]

    markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎬 Movie Bot Ready!\n\n"
        "Type any movie name to search\n"
        "or use buttons below:",
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

    if "subs" not in context.application.bot_data:
        context.application.bot_data["subs"] = set()

    chat_id = update.effective_chat.id

    context.application.bot_data["subs"].add(chat_id)

    await update.message.reply_text(
        "✅ Subscribed!\nDaily movies at 9:00 AM IST"
    )


# ================= AUTO SEARCH =================

async def auto_search(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text.startswith("/"):
        return

    movie = search_movie_by_name(text)

    if not movie:
        await update.message.reply_text("❌ Movie not found")
        return

    poster = movie.get("Poster")

    caption = (
        f"🎬 {movie.get('Title')} ({movie.get('Year')})\n"
        f"⭐ IMDb: {movie.get('imdbRating')}\n\n"
        f"{movie.get('Plot')}"
    )

    keyboard = [[
        InlineKeyboardButton(
            "View on IMDb",
            url=f"https://www.imdb.com/title/{movie.get('imdbID')}/"
        )
    ]]

    markup = InlineKeyboardMarkup(keyboard)

    try:

        if poster and poster != "N/A":

            await update.message.reply_photo(
                photo=poster,
                caption=caption,
                reply_markup=markup
            )

        else:

            await update.message.reply_text(
                caption,
                reply_markup=markup
            )

    except Exception as e:
        print(e)


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
                f"⭐ IMDb: {details.get('imdbRating')}\n\n"
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

    print("Bot starting...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.bot_data["subs"] = set()

    # handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("latest", latest))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_search))

    # daily job at 9 AM IST
    app.job_queue.run_daily(
        daily_job,
        time=datetime.time(hour=9, minute=0, tzinfo=IST)
    )

    print("Bot running!")

    app.run_polling()


# ================= RUN =================

if __name__ == "__main__":
    main()