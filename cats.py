import asyncio
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from config import TOKEN, THE_CAT_API_KEY
import aiohttp

router = Router()

# --- HTTP helpers ------------------------------------------------------------

async def fetch_json(session: aiohttp.ClientSession, url: str, *, headers=None, params=None):
    async with session.get(url, headers=headers, params=params, timeout=15) as resp:
        resp.raise_for_status()
        return await resp.json()

async def get_cat_breeds(session: aiohttp.ClientSession):
    url = "https://api.thecatapi.com/v1/breeds"
    headers = {"x-api-key": THE_CAT_API_KEY}
    return await fetch_json(session, url, headers=headers)

async def get_cat_image_by_breed(session: aiohttp.ClientSession, breed_id: str):
    url = "https://api.thecatapi.com/v1/images/search"
    headers = {"x-api-key": THE_CAT_API_KEY}
    params = {"breed_ids": breed_id, "limit": 1, "size": "med"}
    data = await fetch_json(session, url, headers=headers, params=params)
    if isinstance(data, list) and data and data[0].get("url"):
        return data[0]["url"]
    return None

async def get_breed_info(session: aiohttp.ClientSession, breed_name: str):
    breeds = await get_cat_breeds(session)
    if not isinstance(breeds, list):
        return None

    name_lower = (breed_name or "").strip().lower()

    # Точное совпадение
    for b in breeds:
        if b.get("name", "").lower() == name_lower:
            return b

    # Частичное совпадение (на случай опечаток/части названия)
    for b in breeds:
        if name_lower and name_lower in b.get("name", "").lower():
            return b

    return None

# --- Handlers ----------------------------------------------------------------

@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привет! Напиши название породы кошки (англ. название, например: Bengal, Siamese, Siberian), "
        "и я пришлю фото и краткую информацию."
    )

@router.message()
async def send_cat_info(message: Message):
    breed_name = message.text or ""
    async with aiohttp.ClientSession() as session:
        breed_info = await get_breed_info(session, breed_name)

        if not breed_info:
            await message.answer(
                "Порода не найдена. Проверьте написание (обычно TheCatAPI использует английские названия, "
                "например: Bengal, British Shorthair, Siberian)."
            )
            return

        image_url = await get_cat_image_by_breed(session, breed_info["id"])
        info = (
            f"Порода: {breed_info.get('name', '—')}\n"
            f"Описание: {breed_info.get('description', '—')}\n"
            f"Продолжительность жизни: {breed_info.get('life_span', '—')} лет"
        )

        if image_url:
            await message.answer_photo(photo=image_url, caption=info)
        else:
            await message.answer(info + "\n\n(Изображение найти не удалось.)")

# --- Entry point -------------------------------------------------------------

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
