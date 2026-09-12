import asyncio
import os
from datetime import datetime, timezone
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from supabase import create_client, Client

BOT_TOKEN = "8949900050:AAHEr-z4Mzchp7mKecY_XiW4WUobbdheVxs"
SUPABASE_URL = "https://tdnvnbpyuiwuytpaucih.supabase.co/rest/v1/"
SUPABASE_KEY = "sb_secret_ZcvykeAJeRCF2PEZiwh4VA_gvz2sq62" # Берется из Project Settings -> API Keys -> Secret keys (service_role)
WEBAPP_URL = "https://varivon2283.github.io/slysh-cho-game/"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Клавиатура с кнопкой запуска
def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👊 Выйти на район", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])

@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    user = message.from_user
    ref_arg = command.args  # Параметр из ссылки ?start=XXXXX

    print(f"--> /start от пользователя {user.id} ({user.first_name}), реферал arg: {ref_arg}")

    try:
        # 1. Проверяем, есть ли пользователь в базе
        res = supabase.table("players").select("*").eq("tg_id", user.id).execute()
        
        is_new_user = not res.data or len(res.data) == 0

        if is_new_user:
            print(f"Новый пацан на районе! Регаем ID: {user.id}")
            supabase.table("players").insert({
                "tg_id": user.id,
                "name": user.first_name,
                "seeds": 50,
                "phones": 2,
                "energy": 50
            }).execute()

            # 2. Проверяем реферальную ссылку
            if ref_arg and ref_arg.isdigit():
                inviter_id = int(ref_arg)

                # Нельзя пригласить самого себя
                if inviter_id != user.id:
                    print(f"Начисляем бонус пригласившему ID: {inviter_id}")
                    inv_res = supabase.table("players").select("*").eq("tg_id", inviter_id).execute()
                    
                    if inv_res.data and len(inv_res.data) > 0:
                        inv = inv_res.data[0]
                        current_seeds = inv.get("seeds") or 0
                        current_phones = inv.get("phones") or 0
                        current_friends = inv.get("friends") or 0

                        supabase.table("players").update({
                            "seeds": current_seeds + 100,
                            "phones": current_phones + 1,
                            "friends": current_friends + 1
                        }).eq("tg_id", inviter_id).execute()

                        # Отправляем победный пуш пригласившему
                        try:
                            await bot.send_message(
                                chat_id=inviter_id,
                                text=(
                                    f"👊 Твой кореш <b>{user.first_name}</b> залетел на район!\n"
                                    f"В общак упало: <b>+100 🌻</b> и <b>+1 📱</b>!"
                                ),
                                parse_mode="HTML"
                            )
                            print(f"Уведомление успешно доставлено пацану {inviter_id}!")
                        except Exception as send_err:
                            print(f"Не удалось отправить сообщение {inviter_id}: {send_err}")
                    else:
                        print(f"Пригласивший ID {inviter_id} не найден в таблице players.")
                else:
                    print("Попытка пригласить самого себя проигнорирована.")
        else:
            print(f"Пользователь {user.id} уже есть в базе — бонус не начисляется повторно.")

    except Exception as e:
        print(f"Критическая ошибка БД при /start: {e}")

    # Отправляем приветствие с кнопкой запуска
    await message.answer(
        f"Здорово, <b>{user.first_name}</b>! Добро пожаловать на район.\nЖми кнопку ниже, чтобы начать поднимать авторитет!",
        reply_markup=get_main_kb(),
        parse_mode="HTML"
    )

# Фоновая задача: проверка восстановившейся энергии и рассылка пушей
async def energy_notifier_loop():
    while True:
        try:
            # Ищем игроков, у кого энергия восстановилась до 50
            res = supabase.table("players").select("tg_id, name, energy").eq("energy", 50).execute()
            if res.data:
                for player in res.data:
                    # Чтобы не спамить постоянно, в реальном проекте ставится флаг notification_sent
                    pass
        except Exception as e:
            print(f"Ошибка в цикле пушей: {e}")
        
        await asyncio.sleep(180) # Проверка раз в 3 минуты

# Веб-сервер для удержания бесплатного порта на Render
async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await start_web_server()
    asyncio.create_task(energy_notifier_loop())
    print("Бот запущен и мониторит район...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
