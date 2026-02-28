import os
import requests
import datetime
import random
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
    "kannada",
    "korean",
    "japanese",
    "spanish"
]

SEARCH_KEYWORDS = [
    "love",
    "action",
    "life",
    "hero",
    "story",
    "night",
    "day",
    "war",
    "king",
    "queen"
]

# ================= YOUTUBE =================

def youtube_search(query):
    return f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"


# ================= MENU =================

def main_menu_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton("🎲 Random", callback_data="random"),
            InlineKeyboardButton("🔥 Latest", callback_data="latest")
        ],

        [
            InlineKeyboardButton("🇮🇳 Malayalam", callback_data="lang_malayalam"),
            InlineKeyboardButton("🇺🇸 English", callback_data="lang_english")
        ],

        [
            InlineKeyboardButton("🇮🇳 Hindi", callback_data="lang_hindi"),
            InlineKeyboardButton("🇮🇳 Tamil", callback_data="lang_tamil")
        ],

        [
            InlineKeyboardButton("🇮🇳 Telugu", callback_data="lang_telugu"),
            InlineKeyboardButton("🇮🇳 Kannada", callback_data="lang_kannada")
        ],

        [
            InlineKeyboardButton("🇰🇷 Korean", callback_data="lang_korean"),
            InlineKeyboardButton("🇯🇵 Japanese", callback_data="lang_japanese")
        ],

        [
            InlineKeyboardButton("🇪🇸 Spanish", callback_data="lang_spanish")
        ],

        [
            InlineKeyboardButton("✅ Subscribe", callback_data="subscribe")
        ]

    ])


# ================= OMDB HELPERS =================

def get_movie_details(imdb_id):

    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&i={imdb_id}&plot=full"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()

        if data.get("Response") == "True":
            return data
    except:
        pass

    return None


# ================= FETCH LATEST =================

def fetch_latest_movies():

    year = datetime.datetime.now().year

    results = []

    for keyword in SEARCH_KEYWORDS:

        url = f"https://www.omdbapi.com/?apikey={OMDB_API}&s={keyword}&y={year}"

        try:

            res = requests.get(url, timeout=10)
            data = res.json()

            if data.get("Response") != "True":
                continue

            for movie in data.get("Search", []):

                details = get_movie_details(movie["imdbID"])

                if details:
                    results.append(details)

                if len(results) >= 10:
                    return results

        except:
            pass

    return results


# ================= FETCH BY LANGUAGE =================

def fetch_latest_by_language(language):

    year = datetime.datetime.now().year

    results = []

    for keyword in SEARCH_KEYWORDS:

        url = f"https://www.omdbapi.com/?apikey={OMDB_API}&s={keyword}&y={year}"

        try:

            res = requests.get(url, timeout=10)
            data = res.json()

            if data.get("Response") != "True":
                continue

            for movie in data["Search"]:

                details = get_movie_details(movie["imdbID"])

                if not details:
                    continue

                lang = details.get("Language", "").lower()

                if language.lower() in lang:

                    results.append(details)

                if len(results) >= 5:
                    return results

        except:
            pass

    return results


# ================= RANDOM =================

def fetch_random_movie():

    year = random.randint(2000, datetime.datetime.now().year)

    keyword = random.choice(SEARCH_KEYWORDS)

    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&s={keyword}&y={year}"

    try:

        res = requests.get(url, timeout=10)
        data = res.json()

        if data.get("Response") == "True":

            movie = random.choice(data["Search"])

            return get_movie_details(movie["imdbID"])

    except:
        pass

    return None


# ================= SEARCH =================

def search_movies(query):

    query = query.lower()

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

    if not movie_name:
        movie_name = query

    url = f"https://www.omdbapi.com/?apikey={OMDB_API}&s={movie_name}"

    try:

        res = requests.get(url, timeout=10)
        data = res.json()

        if data.get("Response") != "True":
            return []

        results = []

        for movie in data["Search"]:

            details = get_movie_details(movie["imdbID"])

            if not details:
                continue

            lang = details.get("Language", "").lower()
            year = details.get("Year", "")

            if selected_language and selected_language not in lang:
                continue

            if selected_year and selected_year not in year:
                continue

            results.append(details)

        return results[:10]

    except:
        return []


# ================= SEND =================

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

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton("▶ Trailer",
                url=youtube_search(f"{title} trailer")),

            InlineKeyboardButton("🎞 Teaser",
                url=youtube_search(f"{title} teaser"))
        ],

        [
            InlineKeyboardButton("⭐ IMDb",
                url=f"https://www.imdb.com/title/{imdb_id}/")
        ],

        [
            InlineKeyboardButton("🏠 Menu", callback_data="start")
        ]

    ])

    if poster and poster != "N/A":

        await bot.send_photo(
            chat_id=chat_id,
            photo=poster,
            caption=caption,
            reply_markup=keyboard
        )

    else:

        await bot.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=keyboard
        )


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🎬 Movie Bot Ready!\n\n"
        "Send movie name, language, year or description\n\n"
        "Examples:\n"
        "Drishyam malayalam\n"
        "Avengers 2012\n"
        "Tamil action movie"
    )

    if update.message:

        await update.message.reply_text(text,
            reply_markup=main_menu_keyboard())

    else:

        await update.callback_query.message.reply_text(text,
            reply_markup=main_menu_keyboard())


# ================= AUTO SEARCH =================

async def auto_search(update: Update, context: ContextTypes.DEFAULT_TYPE):

    movies = search_movies(update.message.text)

    if not movies:

        await update.message.reply_text("❌ No movies found",
            reply_markup=main_menu_keyboard())
        return

    keyboard = []

    for movie in movies:

        keyboard.append([

            InlineKeyboardButton(
                f"{movie['Title']} ({movie['Year']}) • {movie['Language']}",
                callback_data=f"movie_{movie['imdbID']}"
            )

        ])

    await update.message.reply_text(
        "🎬 Select movie:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= BUTTON =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    if query.data == "start":

        await start(update, context)

    elif query.data == "latest":

        movies = fetch_latest_movies()

        for m in movies:

            await send_movie(query.message.chat_id, m, context.bot)

    elif query.data == "random":

        movie = fetch_random_movie()

        if movie:

            await send_movie(query.message.chat_id, movie, context.bot)

    elif query.data.startswith("lang_"):

        lang = query.data.replace("lang_", "")

        movies = fetch_latest_by_language(lang)

        if not movies:

            await query.message.reply_text(f"No {lang} movies found")

            return

        for movie in movies:

            await send_movie(query.message.chat_id, movie, context.bot)

    elif query.data.startswith("movie_"):

        imdb_id = query.data.replace("movie_", "")

        movie = get_movie_details(imdb_id)

        if movie:

            await send_movie(query.message.chat_id, movie, context.bot)

    elif query.data == "subscribe":

        subs = context.application.bot_data.setdefault("subs", set())

        subs.add(query.message.chat_id)

        await query.message.reply_text("✅ Subscribed!")


# ================= DAILY =================

async def daily_job(context):

    subs = context.application.bot_data.get("subs", set())

    movies = fetch_latest_movies()

    for chat_id in subs:

        for movie in movies:

            await send_movie(chat_id, movie, context.bot)


# ================= MAIN =================

def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.bot_data["subs"] = set()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_search))

    app.job_queue.run_daily(
        daily_job,
        time=datetime.time(hour=9, tzinfo=IST)
    )

    print("Bot running...")

    app.run_polling()


if __name__ == "__main__":
    main()