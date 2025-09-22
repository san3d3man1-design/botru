import os
import asyncio
import asyncpg
import secrets
import time
from decimal import Decimal
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID") or 0)
BOT_WALLET_ADDRESS = os.getenv("BOT_WALLET_ADDRESS", "YOUR_WALLET")
FEE_PERCENT = Decimal(os.getenv("FEE_PERCENT") or "3.0")
DATABASE_URL = os.getenv("DATABASE_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
pool = None  # Postgres pool

# ----------------- GIFS (File IDs oder lokale Dateien einsetzen) -----------------
GIFS = {
    "wallet": "wallet_file_id_here",
    "start_menu": "start_file_id_here",
    "deal_create": "deal_create_file_id_here",
    "deal_done": "deal_done_file_id_here",
    "payment_received": "payment_received_file_id_here"
}

# ----------------- TRANSLATIONS -----------------
TEXTS = {
    "en": {
        "welcome": (
            "👋 **Welcome!**\n\n"
            "💼 Reliable service for secure transactions!\n"
            "✨ Automated, fast, and hassle-free!\n\n"
            "```"
            "🔷 Service fee: only 3 %\n"
            "🔷 Support 24/7: @rdmcd\n"
            "🔷 User reviews: @tonundrwrld"
            "```\n\n"
            "💌❤️ Now your transactions are protected! 🛡️"
        ),
        "new_deal": "📄 New Deal",
        "my_deals": "🔎 My Deals",
        "my_wallet": "💰 My wallet",
        "change_lang": "🌐 Change Language",
        "ask_amount": "💰 Please enter the **amount in TON** for this deal.\n\nExample: `10.5`",
        "ask_desc": "📝 Great!\n\nNow enter a **short description** of the gift / NFT / service you are selling.",
        "deal_created": "✅ Deal successfully created!",
        "menu": "📋 Main Menu:",
        "choose_lang": "🌐 Please choose your language:",
        "no_deals": "ℹ️ You don’t have any deals yet.",
        "deal_paid": "✅ Payment for deal {token} confirmed.",
        "deal_received": "📦 Buyer confirmed receipt for deal {token}.",
        "deal_payout": "💸 Payout for deal {token} completed.\n\nAmount: {amount} TON\nFee: {fee} TON",
        "deal_cancel": "❌ Deal {token} was cancelled.",
        "system_confirms": "⏳ The system will confirm automatically once payment is received.",
        "deal_not_found": "⚠️ Deal not found.",
        "wallet_set": (
            "✅ Great! Your TON wallet has been saved:\n`{wallet}`\n\n"
            "You can update it anytime by sending a new address."
        ),
        "wallet_current": "👛 *Current wallet:*\n`{wallet}`\n\nIf you want to change it, send a new one below 👇",
        "wallet_none": (
            "ℹ️ To use @GiftedGuarantBot, you need to link your TON wallet.\n\n"
            "This allows us to securely process your deals and payouts. "
            "Don’t worry – you can change your wallet anytime.\n\n"
            "👉 Please send your TON wallet address below to get started."
        ),
    },
    "uk": {
        "welcome": (
            "👋 **Ласкаво просимо!**\n\n"
            "💼 Надійний сервіс для безпечних транзакцій!\n"
            "✨ Автоматизовано, швидко та без клопоту!\n\n"
            "```"
            "🔷 Комісія сервісу: лише 3 %\n"
            "🔷 Підтримка 24/7: @rdmcd\n"
            "🔷 Відгуки користувачів: @tonundrwrld"
            "```\n\n"
            "💌❤️ Тепер ваші транзакції захищені! 🛡️"
        ),
        "new_deal": "📄 Нова угода",
        "my_deals": "🔎 Мої угоди",
        "my_wallet": "💰 Мій гаманець",
        "change_lang": "🌐 Змінити мову",
        "ask_amount": "💰 Введіть **суму в TON** для цієї угоди.\n\nПриклад: `10.5`",
        "ask_desc": "📝 Чудово!\n\nТепер введіть **короткий опис** подарунка / NFT / послуги, яку ви продаєте.",
        "deal_created": "✅ Угоду успішно створено!",
        "menu": "📋 Головне меню:",
        "choose_lang": "🌐 Будь ласка, оберіть мову:",
        "no_deals": "ℹ️ У вас ще немає угод.",
        "deal_paid": "✅ Платіж за угоду {token} підтверджено.",
        "deal_received": "📦 Покупець підтвердив отримання за угодою {token}.",
        "deal_payout": "💸 Виплату за угодою {token} завершено.\n\nСума: {amount} TON\nКомісія: {fee} TON",
        "deal_cancel": "❌ Угоду {token} скасовано.",
        "system_confirms": "⏳ Система підтвердить автоматично після отримання платежу.",
        "deal_not_found": "⚠️ Угоду не знайдено.",
        "wallet_set": (
            "✅ Чудово! Ваш TON гаманець збережено:\n`{wallet}`\n\n"
            "Ви можете змінити його будь-коли, надіславши нову адресу."
        ),
        "wallet_current": "👛 *Поточний гаманець:*\n`{wallet}`\n\nЯкщо хочете змінити — введіть новий 👇",
        "wallet_none": (
            "ℹ️ Щоб користуватися @GiftedGuarantBot, потрібно додати свій TON гаманець.\n\n"
            "Це дозволяє нам безпечно обробляти ваші угоди та виплати. "
            "Не хвилюйтеся – ви завжди зможете змінити адресу.\n\n"
            "👉 Надішліть адресу вашого TON гаманця нижче, щоб почати."
        ),
    }
}

# ----------------- DB INIT -----------------
async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, ssl="require")
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS deals (
            id SERIAL PRIMARY KEY,
            deal_token TEXT UNIQUE,
            seller_id BIGINT,
            seller_name TEXT,
            amount TEXT,
            description TEXT,
            status TEXT,
            buyer_id BIGINT,
            payment_token TEXT,
            created_at BIGINT
        )
        """)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id BIGINT PRIMARY KEY,
            name TEXT,
            lang TEXT DEFAULT 'en',
            wallet TEXT
        )
        """)

# ----------------- HELPERS -----------------
async def get_lang(uid):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT lang FROM users WHERE tg_id=$1", uid)
    return row["lang"] if row else "en"

def main_menu(lang="en"):
    t = TEXTS[lang]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["new_deal"], callback_data="create_deal")],
        [InlineKeyboardButton(text=t["my_deals"], callback_data="my_deals")],
        [InlineKeyboardButton(text=t["my_wallet"], callback_data="my_wallet")],
        [InlineKeyboardButton(text=t["change_lang"], callback_data="change_lang")]
    ])
    return kb

# ----------------- DEBUG HANDLER (File IDs ausgeben) -----------------
@dp.message()
async def debug_file_id(message: types.Message):
    if message.animation:
        await message.answer(f"Animation file_id: `{message.animation.file_id}`")
    elif message.video:
        await message.answer(f"Video file_id: `{message.video.file_id}`")
    else:
        await message.answer("❌ Dies ist kein GIF/Video, bitte sende eine Animation oder ein Video.")

# ----------------- STARTUP -----------------
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
