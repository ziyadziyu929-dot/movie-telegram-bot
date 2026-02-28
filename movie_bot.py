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


# ================= MULTI SEARCH =================

def search_movies(query):

    query = query.lower().strip()

    selected_language = None
    selected_year = None

    words = query.split()

    movie_words = []

    for word in words:

        if word in SUPPORTED_LANGUAGES:
            selected_language = word

        elif word.isdigit() and len(word) == 4:
            selected_year = word

        else:
            movie_words.append(word)

    movie_name = " ".join(movie_words)

    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&s={movie_name}&type=movie"

    try:

        res = requests.get(url, timeout=15)
        data = res.json()

        if data.get("Response") != "True":
            return []

        results = []

        for movie in data.get("Search", [])[:10]:

            details = get_movie_details(movie["imdbID"])

            if not details:
                continue

            language = details.get("Language", "").lower()
            year = details.get("Year", "")

            # language filter
            if selected_language and selected_language not in language:
                continue

            # year filter
            if selected_year and selected_year not in year:
                continue

            results.append(details)

        return results

    except Exception as e:
        print(e)
        return []


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
        "Examples:\n"
        "Drishyam\n"
        "Drishyam malayalam\n"
        "Drishyam 2013\n"
        "Drishyam part 2 malayalam\n\n"
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

    query = update.message.text

    movies = search_movies(query)

    if not movies:

        await update.message.reply_text("❌ No movies found")
        return

    keyboard = []

    for movie in movies:

        title = movie.get("Title")
        year = movie.get("Year")
        language = movie.get("Language")
        imdb_id = movie.get("imdbID")

        keyboard.append([

            InlineKeyboardButton(
                f"{title} ({year}) • {language}",
                callback_data=f"movie_{imdb_id}"
            )

        ])

    await update.message.reply_text(

        "🎬 Select movie:",

        reply_markup=InlineKeyboardMarkup(keyboard)

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

    elif query.data.startswith("movie_"):

        imdb_id = query.data.replace("movie_", "")

        movie = get_movie_details(imdb_id)

        if movie:

            await send_movie(
                query.message.chat_id,
                movie,
                context.bot
            )


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