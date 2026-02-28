import os
import asyncio
import random
import aiohttp
from datetime import date

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

if not TMDB_API_KEY:
    raise ValueError("TMDB_API_KEY missing")

BASE_URL = "https://api.themoviedb.org/3"
POSTER_URL = "https://image.tmdb.org/t/p/w500"
YOUTUBE_URL = "https://www.youtube.com/watch?v="

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

USER_CHATS = set()

# ================= LANGUAGES =================

LANGUAGES = {
    "🇮🇳 Malayalam": "ml",
    "🇮🇳 Tamil": "ta",
    "🇮🇳 Telugu": "te",
    "🇮🇳 Hindi": "hi",
    "🇺🇸 English": "en"
}

# Malayalam priority higher
LANG_PRIORITY = ["ml","ml","ml","ml","ta","te","hi","en"]

# ================= KEYBOARDS =================

main_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
main_keyboard.add("🔥 Latest Movies")
main_keyboard.add("🎬 Popular Movies")
main_keyboard.add("🎲 Random Latest Movies")

language_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
for lang in LANGUAGES:
    language_keyboard.add(lang)

# ================= FETCH =================

async def fetch_json(url):

    async with aiohttp.ClientSession() as session:

        async with session.get(url) as resp:

            if resp.status != 200:
                print("TMDB ERROR:", resp.status)
                return {}

            return await resp.json()

# ================= TRAILER =================

async def get_trailer(movie_id):

    url = f"{BASE_URL}/movie/{movie_id}/videos?api_key={TMDB_API_KEY}"

    data = await fetch_json(url)

    for v in data.get("results", []):

        if v["site"] == "YouTube" and v["type"] == "Trailer":
            return YOUTUBE_URL + v["key"]

    return None

# ================= COLLECTION =================

async def get_collection(movie_id):

    url = f"{BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}"

    data = await fetch_json(url)

    collection = data.get("belongs_to_collection")

    if not collection:
        return []

    url2 = f"{BASE_URL}/collection/{collection['id']}?api_key={TMDB_API_KEY}"

    data2 = await fetch_json(url2)

    return data2.get("parts", [])

# ================= SEND MOVIE =================

async def send_movie(chat_id, movie):

    title = movie.get("title", "Unknown")
    release = movie.get("release_date", "Unknown")
    rating = movie.get("vote_average", "N/A")
    overview = movie.get("overview", "No description")
    poster = movie.get("poster_path")
    movie_id = movie.get("id")

    trailer = await get_trailer(movie_id)

    caption = f"""
🎬 {title}

📅 Release: {release}
⭐ Rating: {rating}

📝 {overview[:500]}
"""

    markup = None

    if trailer:
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton("▶ Watch Trailer", url=trailer)
        )

    if poster:
        await bot.send_photo(
            chat_id,
            POSTER_URL + poster,
            caption=caption,
            reply_markup=markup
        )
    else:
        await bot.send_message(chat_id, caption, reply_markup=markup)

    # show parts
    parts = await get_collection(movie_id)

    if parts:
        await bot.send_message(chat_id, "🎞 Movie Parts:")

        for p in parts:
            await bot.send_message(
                chat_id,
                f"{p['title']} ({p.get('release_date','')})"
            )

# ================= SEARCH =================

async def search_movie(query):

    url = f"{BASE_URL}/search/movie?api_key={TMDB_API_KEY}&query={query}"

    data = await fetch_json(url)

    return data.get("results", [])

# ================= LATEST (FIXED Malayalam) =================

async def latest_movies(lang):

    code = LANGUAGES.get(lang, "ml")

    today = date.today()

    url = (
        f"{BASE_URL}/discover/movie"
        f"?api_key={TMDB_API_KEY}"
        f"&with_original_language={code}"
        f"&region=IN"
        f"&sort_by=primary_release_date.desc"
        f"&primary_release_date.lte={today}"
        f"&vote_count.gte=1"
        f"&page=1"
    )

    data = await fetch_json(url)

    return data.get("results", [])

# ================= POPULAR =================

async def popular_movies():

    code = random.choice(LANG_PRIORITY)

    url = (
        f"{BASE_URL}/discover/movie"
        f"?api_key={TMDB_API_KEY}"
        f"&with_original_language={code}"
        f"&region=IN"
        f"&sort_by=popularity.desc"
        f"&vote_count.gte=10"
        f"&page=1"
    )

    data = await fetch_json(url)

    return data.get("results", [])

# ================= RANDOM =================

async def random_movies():

    code = random.choice(LANG_PRIORITY)

    page = random.randint(1,5)

    url = (
        f"{BASE_URL}/discover/movie"
        f"?api_key={TMDB_API_KEY}"
        f"&with_original_language={code}"
        f"&region=IN"
        f"&sort_by=primary_release_date.desc"
        f"&page={page}"
    )

    data = await fetch_json(url)

    results = data.get("results", [])

    if not results:
        return []

    return random.sample(results, min(5, len(results)))

# ================= AUTO UPDATE =================

async def auto_update():

    await asyncio.sleep(15)

    while True:

        print("Auto update running")

        movies = await popular_movies()

        for chat in USER_CHATS:

            for m in movies[:3]:

                await send_movie(chat, m)

        await asyncio.sleep(21600)

# ================= HANDLERS =================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):

    USER_CHATS.add(message.chat.id)

    await message.answer(
        "🎬 Movie Bot Ready",
        reply_markup=main_keyboard
    )

@dp.message_handler(lambda m: m.text == "🔥 Latest Movies")
async def choose_lang(message: types.Message):

    await message.answer(
        "Choose language:",
        reply_markup=language_keyboard
    )

@dp.message_handler(lambda m: m.text in LANGUAGES)
async def latest_lang(message: types.Message):

    await message.answer("Fetching latest movies...")

    movies = await latest_movies(message.text)

    if not movies:

        await message.answer("No movies found")
        return

    for m in movies[:5]:
        await send_movie(message.chat.id, m)

@dp.message_handler(lambda m: m.text == "🎬 Popular Movies")
async def popular_handler(message: types.Message):

    movies = await popular_movies()

    for m in movies[:5]:
        await send_movie(message.chat.id, m)

@dp.message_handler(lambda m: m.text == "🎲 Random Latest Movies")
async def random_handler(message: types.Message):

    movies = await random_movies()

    for m in movies:
        await send_movie(message.chat.id, m)

@dp.message_handler()
async def search_handler(message: types.Message):

    movies = await search_movie(message.text)

    if not movies:
        await message.answer("Movie not found")
        return

    for m in movies[:3]:
        await send_movie(message.chat.id, m)

# ================= START =================

async def on_startup(dp):

    asyncio.create_task(auto_update())

if __name__ == "__main__":

    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)