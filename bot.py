import asyncio
import os
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
    ref_id = command.args  # ID того, кто пригласил

    # Проверяем, есть ли уже этот пацан в базе
    res = supabase.table("players").select("*").eq("tg_id", user.id).execute()
    
    if not res.data:
        # Новый игрок — регистрируем
        supabase.table("players").insert({
            "tg_id": user.id,
            "name": user.first_name,
            "seeds": 50,
            "phones": 2,
            "energy": 50
        }).execute()

        # Если пришел по реферальной ссылке
        if ref_id and ref_id.isdigit() and int(ref_id) != user.id:
            inviter_id = int(ref_id)
            # Находим пригласившего
            inviter_res = supabase.table("players").select("*").eq("tg_id", inviter_id).execute()
            if inviter_res.data:
                inv = inviter_res.data[0]
                supabase.table("players").update({
                    "seeds": inv["seeds"] + 100,
                    "phones": inv["phones"] + 1,
                    "friends": inv["friends"] + 1
                }).eq("tg_id", inviter_id).execute()

                # Отправляем уведомление пригласившему
                try:
                    await bot.send_message(
                        inviter_id,
                        f"👊 Твой кореш <b>{user.first_name}</b> залетел на район!\nВ общак упало: <b>+100 🌻</b> и <b>+1 📱</b>!",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

    # Кнопка открытия Mini App
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👊 Выйти на район", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])

    await message.answer(
        f"Здорово, <b>{user.first_name}</b>! Добро пожаловать на район.\nЖми кнопку ниже, чтобы начать поднимать авторитет!",
        reply_markup=kb,
        parse_mode="HTML"
    )

async def main():
    print("Бот запущен и следит за районом...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
from aiogram.types import LabeledPrice, PreCheckoutQuery

# Создание счета на оплату 50 Stars за 5 Мобил
@dp.message(lambda msg: msg.text == "/buy_phones")
async def send_stars_invoice(message: types.Message):
    prices = [LabeledPrice(label="5 Мобил 📱", amount=50)] # amount в Stars
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Пакет мобил для района",
        description="5 новеньких мобил 📱 в карман для прокачки и семок",
        payload="buy_phones_5",
        currency="XTR", # XTR — официальный код Telegram Stars
        prices=prices,
        provider_token="" # Для Telegram Stars provider_token всегда оставляется пустым!
    )

# Обязательное подтверждение доступности товара
@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# Начисление после успешной оплаты
@dp.message(lambda msg: msg.successful_payment is not None)
async def process_successful_payment(message: types.Message):
    payment = message.successful_payment
    user_id = message.from_user.id
    
    if payment.invoice_payload == "buy_phones_5":
        # Начисляем 5 мобил в Supabase
        res = supabase.table("players").select("phones").eq("tg_id", user_id).single().execute()
        if res.data:
            new_phones = res.data["phones"] + 5
            supabase.table("players").update({"phones": new_phones}).eq("tg_id", user_id).execute()
            await message.answer("✅ Барыга подогнал товар! 5 мобил 📱 упали на твой счет в игре.")
