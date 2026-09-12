import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from supabase import create_client, Client

# ТВОИ ДАННЫЕ
BOT_TOKEN = "8949900050:AAHEr-z4Mzchp7mKecY_XiW4WUobbdheVxs"
SUPABASE_URL = "https://tdnvnbpyuiwuytpaucih.supabase.co/rest/v1/"
SUPABASE_KEY = "sb_secret_ZcvykeAJeRCF2PEZiwh4VA_gvz2sq62" # Берется из Project Settings -> API Keys -> Secret keys (service_role)
WEBAPP_URL = "https://varivon2283.github.io/slysh-cho-game/"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    user = message.from_user
    ref_id = command.args

    try:
        res = supabase.table("players").select("*").eq("tg_id", user.id).execute()
        if not res.data:
            supabase.table("players").insert({
                "tg_id": user.id,
                "name": user.first_name,
                "seeds": 50,
                "phones": 2,
                "energy": 50
            }).execute()

            if ref_id and ref_id.isdigit() and int(ref_id) != user.id:
                inviter_id = int(ref_id)
                inviter_res = supabase.table("players").select("*").eq("tg_id", inviter_id).execute()
                if inviter_res.data:
                    inv = inviter_res.data[0]
                    supabase.table("players").update({
                        "seeds": inv["seeds"] + 100,
                        "phones": inv["phones"] + 1,
                        "friends": inv["friends"] + 1
                    }).eq("tg_id", inviter_id).execute()

                    try:
                        await bot.send_message(
                            inviter_id,
                            f"👊 Твой кореш <b>{user.first_name}</b> залетел на район!\nВ общак упало: <b>+100 🌻</b> и <b>+1 📱</b>!",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
    except Exception as e:
        print(f"Ошибка БД: {e}")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👊 Выйти на район", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])

    await message.answer(
        f"Здорово, <b>{user.first_name}</b>! Добро пожаловать на район.\nЖми кнопку ниже, чтобы начать поднимать авторитет!",
        reply_markup=kb,
        parse_mode="HTML"
    )

# Мини веб-сервер для прохождения проверки портов Render
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Фиктивный веб-сервер слушает порт {port}")

async def main():
    await start_web_server()
    print("Бот запущен и следит за районом...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
