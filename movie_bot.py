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

SUPPORTED_LANGUAGES = [
    "malayalam",
    "tamil",
    "hindi",
    "english",
    "telugu",
    "kannada"
]

# ================= YOUTUBE =================

def youtube_search(query):
    return f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"

# ================= OMDB HELPERS =================

def fetch_latest_movies():

    year = datetime.datetime.now().year

    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&s=movie&y={year}&type=movie"

    try:
        res = requests.get(url, timeout=15)
        data = res.json()

        if data.get("Response") == "True":
            return data.get("Search", [])[:5]

    except Exception as e:
        print(e)

    return []


def get_movie_details(imdb_id):

    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&i={imdb_id}"

    try:
        res = requests.get(url, timeout=15)
        return res.json()

    except Exception as e:
        print(e)
        return None


# ================= SMART SEARCH =================

def search_movie(query):

    query = query.lower().strip()

    selected_language = None
    movie_name = query

    # detect language
    for lang in SUPPORTED_LANGUAGES:

        if query.endswith(lang):

            selected_language = lang
            movie_name = query.replace(lang, "").strip()
            break

    # search all matches
    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&s={movie_name}"

    try:

        res = requests.get(url, timeout=15)
        data = res.json()

        if data.get("Response") != "True":
            return None

        results = data.get("Search", [])

        best_match = None

        for movie in results:

            details = get_movie_details(movie["imdbID"])

            if not details:
                continue

            title = details.get("Title", "").lower()
            language = details.get("Language", "").lower()

            # exact title + language match
            if selected_language:
                if selected_language in language and movie_name == title:
                    return details

            # language match fallback
            if selected_language and selected_language in language:
                best_match = details

            # exact title fallback
            if movie_name == title:
                best_match = details

        return best_match

    except Exception as e:
        print(e)
        return None


# ================= SEND MOVIE =================

async def send_movie(chat_id, movie, bot):

    title = movie.get("Title")
    year = movie.get("Year")
    rating = movie.get("imdbRating")
    plot = movie.get("Plot")
    poster = movie.get("Poster")
    imdb_id = movie.get("imdbID")
    language = movie.get("Language")

    caption = (
        f"🎬 {title} ({year})\n"
        f"🌐 Language: {language}\n"
        f"⭐ IMDb: {rating}\n\n"
        f"{plot}"
    )

    trailer = youtube_search(f"{title} {language} trailer")
    teaser = youtube_search(f"{title} {language} teaser")

    keyboard = [

        [
            InlineKeyboardButton("▶ Trailer", url=trailer),
            InlineKeyboardButton("🎞 Teaser", url=teaser)
        ],

        [
            InlineKeyboardButton(
                "⭐ IMDb",
                url=f"https://www.imdb.com/title/{imdb_id}/"
            )
        ]

    ]

    markup = InlineKeyboardMarkup(keyboard)

    try:

        if poster and poster != "N/A":

            await bot.send_photo(
                chat_id=chat_id,
                photo=poster,
                caption=caption,
                reply_markup=markup
            )

        else:

            await bot.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=markup
            )

    except Exception as e:
        print(e)


# ================= COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [

        [InlineKeyboardButton("🔥 Latest Movies", callback_data="latest")],

        [InlineKeyboardButton("✅ Subscribe Daily", callback_data="subscribe")]

    ]

    await update.message.reply_text(

        "🎬 Movie Bot Ready!\n\n"
        "Send movie name like:\n"
        "Drishyam malayalam\n"
        "Drishyam hindi\n"
        "Vikram tamil\n\n"
        "Supports all languages",

        reply_markup=InlineKeyboardMarkup(keyboard)

    )


async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):

    movies = fetch_latest_movies()

    for m in movies:

        details = get_movie_details(m["imdbID"])

        if details:

            await send_movie(
                update.effective_chat.id,
                details,
                context.bot
            )


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):

    subs = context.application.bot_data.setdefault("subs", set())

    subs.add(update.effective_chat.id)

    await update.message.reply_text(
        "✅ Subscribed! Daily at 9 AM IST"
    )


# ================= AUTO SEARCH =================

async def auto_search(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text.startswith("/"):
        return

    movie = search_movie(text)

    if not movie:

        await update.message.reply_text("❌ Movie not found")
        return

    await send_movie(
        update.effective_chat.id,
        movie,
        context.bot
    )


# ================= BUTTON HANDLER =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    if query.data == "latest":

        movies = fetch_latest_movies()

        for m in movies:

            details = get_movie_details(m["imdbID"])

            if details:

                await send_movie(
                    query.message.chat_id,
                    details,
                    context.bot
                )

    elif query.data == "subscribe":

        subs = context.application.bot_data.setdefault("subs", set())

        subs.add(query.message.chat_id)

        await query.message.reply_text("✅ Subscribed!")


# ================= DAILY JOB =================

async def daily_job(context: ContextTypes.DEFAULT_TYPE):

    subs = context.application.bot_data.get("subs", set())

    movies = fetch_latest_movies()

    for chat_id in subs:

        for m in movies:

            details = get_movie_details(m["imdbID"])

            if details:

                await send_movie(
                    chat_id,
                    details,
                    context.bot
                )


# ================= MAIN =================

def main():

    print("Bot starting on Railway...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.bot_data["subs"] = set()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("latest", latest))

    app.add_handler(CommandHandler("subscribe", subscribe))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_search))

    app.job_queue.run_daily(
        daily_job,
        time=datetime.time(hour=9, tzinfo=IST)
    )

    print("Bot running successfully!")

    app.run_polling()


# ================= RUN =================

if __name__ == "__main__":
    main()