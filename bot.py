import asyncio
import os
import json
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, LabeledPrice, PreCheckoutQuery
from supabase import create_client, Client

BOT_TOKEN = "8949900050:AAHEr-z4Mzchp7mKecY_XiW4WUobbdheVxs"
SUPABASE_URL = "https://tdnvnbpyuiwuytpaucih.supabase.co"
SUPABASE_KEY = "sb_secret_ZcvykeAJeRCF2PEZiwh4VA_gvz2sq62" # Берется из Project Settings -> API Keys -> Secret keys (service_role)
WEBAPP_URL = "https://varivon2283.github.io/slysh-cho-game/"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👊 Выйти на район", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])

@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    user = message.from_user
    ref_arg = command.args

    try:
        res = supabase.table("players").select("*").eq("tg_id", user.id).execute()
        is_new_user = not res.data or len(res.data) == 0

        if is_new_user:
            supabase.table("players").insert({
                "tg_id": user.id,
                "name": user.first_name,
                "seeds": 50,
                "phones": 2,
                "energy": 50
            }).execute()

            if ref_arg and ref_arg.isdigit():
                inviter_id = int(ref_arg)
                if inviter_id != user.id:
                    inv_res = supabase.table("players").select("*").eq("tg_id", inviter_id).execute()
                    if inv_res.data:
                        inv = inv_res.data[0]
                        supabase.table("players").update({
                            "seeds": (inv.get("seeds") or 0) + 100,
                            "phones": (inv.get("phones") or 0) + 1,
                            "friends": (inv.get("friends") or 0) + 1
                        }).eq("tg_id", inviter_id).execute()

                        try:
                            await bot.send_message(
                                chat_id=inviter_id,
                                text=f"👊 Твой кореш <b>{user.first_name}</b> залетел на район!\nВ общак упало: <b>+100 🌻</b> и <b>+1 📱</b>!",
                                parse_mode="HTML"
                            )
                        except Exception:
                            pass
    except Exception as e:
        print(f"Ошибка БД при старте: {e}")

    await message.answer(
        f"Здорово, <b>{user.first_name}</b>! Добро пожаловать на район.\nЖми кнопку ниже, чтобы начать поднимать авторитет!",
        reply_markup=get_main_kb(),
        parse_mode="HTML"
    )

# --- ПЛАТЕЖИ TELEGRAM STARS ---

# 1. Telegram требует обязательного подтверждения перед списанием
@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# 2. Успешная оплата: начисление мобил в Supabase
# 2. Успешная оплата: железобетонное начисление мобил в Supabase
@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    payment = message.successful_payment
    user_id = message.from_user.id
    payload_str = payment.invoice_payload

    print(f"--> ПОЛУЧЕНА ОПЛАТА от {user_id}! Payload: {payload_str}")

    phones_to_add = 5  # дефолтное значение

    # Парсим сколько мобил начислить
    try:
        payload = json.loads(payload_str)
        phones_to_add = int(payload.get("phones", 5))
    except Exception as e:
        print(f"Ошибка парсинга payload: {e}, начисляем дефолтные 5")

    try:
        # Ищем игрока в базе (без single(), чтобы не падало)
        res = supabase.table("players").select("phones").eq("tg_id", user_id).execute()
        
        if res.data and len(res.data) > 0:
            current_phones = res.data[0].get("phones") or 0
            new_phones = current_phones + phones_to_add
            
            supabase.table("players").update({
                "phones": new_phones
            }).eq("tg_id", user_id).execute()

            print(f"✅ УСПЕХ: Начислено {phones_to_add} мобил игроку {user_id}. Теперь у него {new_phones} 📱")
            
            await message.answer(
                f"✅ <b>Донат получен!</b> Барыга подогнал <b>+{phones_to_add} 📱</b> в карман!\n"
                f"Перезайди в игру или обнови экран — баланс уже на базе!",
                parse_mode="HTML"
            )
        else:
            print(f"⚠️ Игрок с tg_id {user_id} не найден в таблице players при оплате!")
            # Если почему-то игрока нет, создаем сразу с купленными мобилами
            supabase.table("players").insert({
                "tg_id": user_id,
                "name": message.from_user.first_name,
                "seeds": 50,
                "phones": 2 + phones_to_add,
                "energy": 50
            }).execute()
            await message.answer(
                f"✅ <b>Донат получен!</b> Создан профиль и начислено <b>+{phones_to_add} 📱</b>!",
                parse_mode="HTML"
            )
    except Exception as err:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА записи оплаты в Supabase: {err}")
        await message.answer("Произошла техническая заминка при записи в базу, но оплата зафиксирована! Напиши админу.")

# --- ВЕБ-СЕРВЕР (CORS + Генерация ссылок для Mini App) ---

async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def handle_create_invoice(request):
    # Разрешаем запросы из GitHub Pages (CORS)
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }

    if request.method == "OPTIONS":
        return web.Response(headers=headers)

    try:
        data = await request.json()
        user_id = data.get("tg_id")
        package = data.get("package", "small")

        packages = {
            "small": {"title": "Пачка мобил (5 шт)", "phones": 5, "stars": 25},
            "medium": {"title": "Пакет мобил (15 шт)", "phones": 15, "stars": 65},
            "big": {"title": "Чемодан мобил (50 шт)", "phones": 50, "stars": 199},
        }

        item = packages.get(package, packages["small"])

        # Создаем счет через Telegram Bot API
        invoice_link = await bot.create_invoice_link(
            title=item["title"],
            description=f"Покупка {item['phones']} мобил для прокачки пацана на районе",
            payload=json.dumps({"tg_id": user_id, "phones": item["phones"]}),
            currency="XTR", # Официальная валюта Telegram Stars
            prices=[LabeledPrice(label=item["title"], amount=item["stars"])]
        )

        return web.json_response({"ok": True, "invoice_link": invoice_link}, headers=headers)
    except Exception as e:
        print(f"Ошибка создания счета: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers=headers)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_post("/create-invoice", handle_create_invoice)
    app.router.add_options("/create-invoice", handle_create_invoice)
    
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Веб-сервер и платежи запущены на порту {port}")

async def main():
    await start_web_server()
    print("Бот запущен и следит за районом...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
