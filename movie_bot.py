import os
import random
import asyncio
import aiohttp

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
TMDB_API_KEY = os.getenv("TMDB_API_KEY") or "YOUR_TMDB_API_KEY"

BASE_URL = "https://api.themoviedb.org/3"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ================= LANGUAGE MAP =================

LANGUAGE_MAP = {
    "🇮🇳 Malayalam": "ml",
    "🇮🇳 Tamil": "ta",
    "🇮🇳 Telugu": "te",
    "🇮🇳 Hindi": "hi",
    "🇺🇸 English": "en",
    "🇰🇷 Korean": "ko",
    "🇯🇵 Japanese": "ja",
    "🇨🇳 Chinese": "zh",
    "🇪🇸 Spanish": "es",
}

# Malayalam priority order
LANGUAGE_PRIORITY = [
    "🇮🇳 Malayalam",
    "🇮🇳 Tamil",
    "🇮🇳 Telugu",
    "🇮🇳 Hindi",
    "🇺🇸 English",
    "🇰🇷 Korean",
    "🇯🇵 Japanese",
    "🇨🇳 Chinese",
    "🇪🇸 Spanish",
]

# ================= KEYBOARDS =================

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("🔥 Latest Movies")],
        [KeyboardButton("🎲 Random Latest Movies")],
    ],
    resize_keyboard=True
)

language_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(lang)] for lang in LANGUAGE_PRIORITY],
    resize_keyboard=True
)

# ================= FETCH =================

async def fetch_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# ================= FORMAT =================

def format_movie(movie):

    title = movie.get("title", "Unknown")
    date = movie.get("release_date", "Unknown")
    rating = movie.get("vote_average", "N/A")

    return f"""
🎬 {title}
⭐ Rating: {rating}
📅 Release: {date}
"""

# ================= LATEST BY LANGUAGE =================

async def latest_movies(language):

    code = LANGUAGE_MAP.get(language, "ml")

    # Malayalam gets more pages
    pages = 3 if code == "ml" else 1

    all_movies = []

    for page in range(1, pages+1):

        url = (
            f"{BASE_URL}/discover/movie"
            f"?api_key={TMDB_API_KEY}"
            f"&with_original_language={code}"
            f"&region=IN"
            f"&sort_by=primary_release_date.desc"
            f"&vote_count.gte=5"
            f"&page={page}"
        )

        data = await fetch_json(url)

        results = data.get("results", [])

        all_movies.extend(results)

    return all_movies[:10]

# ================= RANDOM =================

async def random_latest_movies():

    # Malayalam higher chance
    lang_choices = (
        ["ml"] * 5 +
        ["ta","te","hi","en","ko","ja"]
    )

    code = random.choice(lang_choices)

    page = random.randint(1,3)

    url = (
        f"{BASE_URL}/discover/movie"
        f"?api_key={TMDB_API_KEY}"
        f"&with_original_language={code}"
        f"&region=IN"
        f"&sort_by=primary_release_date.desc"
        f"&vote_count.gte=5"
        f"&page={page}"
    )

    data = await fetch_json(url)

    results = data.get("results", [])

    return random.sample(results, min(5, len(results)))

# ================= HANDLERS =================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):

    await message.answer(
        "Welcome!\nChoose option:",
        reply_markup=main_keyboard
    )

# Latest button
@dp.message_handler(lambda message: message.text == "🔥 Latest Movies")
async def choose_language(message: types.Message):

    await message.answer(
        "Choose Language:",
        reply_markup=language_keyboard
    )

# Random button
@dp.message_handler(lambda message: message.text == "🎲 Random Latest Movies")
async def random_movies_handler(message: types.Message):

    movies = await random_latest_movies()

    if not movies:
        await message.answer("No movies found")
        return

    for movie in movies:
        await message.answer(format_movie(movie))

# Language selection
@dp.message_handler(lambda message: message.text in LANGUAGE_MAP)
async def language_movies_handler(message: types.Message):

    language = message.text

    await message.answer(f"Fetching latest {language} movies...")

    movies = await latest_movies(language)

    if not movies:
        await message.answer("No movies found")
        return

    for movie in movies:
        await message.answer(format_movie(movie))

# ================= RUN =================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)