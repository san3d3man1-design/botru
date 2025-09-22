import os
import asyncio
import asyncpg
import secrets
import time
from decimal import Decimal
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",")]  # mehrere Admins möglich
BOT_WALLET_ADDRESS = os.getenv("BOT_WALLET_ADDRESS", "YOUR_WALLET")
FEE_PERCENT = Decimal(os.getenv("FEE_PERCENT") or "3.0")
DATABASE_URL = os.getenv("DATABASE_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
pool = None  # Postgres pool

# ----------------- GIFS -----------------
GIFS = {
    "wallet": "CgACAgUAAxkBAAOQaNEfCaWQid948w6qnzYq_EZYwSQAAtQYAAITBoBW3-ihNesJfSo2BA",
    "start_menu": "CgACAgIAAxkBAAOOaNEfBP6PPCVdEU76pOQ8hi6ZNO8AAl6EAAJa0nFKCJ1Xxe0VHqk2BA",
    "deal_create": "CgACAgUAAxkBAAOSaNEfD-YGFJqMNsoSVqmSJ3M5JGwAAtMYAAITBoBWXrWIw-odYmE2BA",
    "deal_done": "CgACAgIAAxkBAAOUaNEfEVNpxaPJBEJDGptYJVdulGAAAm15AAJoJmhJYzkzz1d-e2I2BA",
    "payment_received": "CgACAgIAAxkBAAOWaNEfHrVg7A-D78-TAQ0uD6V5YS4AAmt5AAJoJmhJ2SdDxqSbm-o2BA"
}

# ----------------- TRANSLATIONS -----------------
TEXTS = {
    "en": {
        "welcome": (
            "👋 **Welcome!**\n\n"
            "💼 Reliable service for secure transactions!\n"
            "✨ Automated, fast, and hassle-free!\n\n"
            "🔷 Service fee: only 3 %\n"
            "🔷 Support 24/7: @rdmcd\n"
            "🔷 User reviews: @tonundrwrld\n\n"
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
            "🔷 Комісія сервісу: лише 3 %\n"
            "🔷 Підтримка 24/7: @rdmcd\n"
            "🔷 Відгуки користувачів: @tonundrwrld\n\n"
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

# ----------------- START with deep link (Buyer Link) -----------------
@dp.message(CommandStart(deep_link=True))
async def cmd_start_with_link(message: types.Message, command: CommandStart):
    uid = message.from_user.id
    lang = await get_lang(uid)
    token = command.args

    if token and token.startswith("join_"):
        deal_token = token.replace("join_", "")
        async with pool.acquire() as conn:
            await conn.execute("UPDATE deals SET buyer_id=$1 WHERE deal_token=$2", uid, deal_token)
            deal = await conn.fetchrow("SELECT amount,description,payment_token FROM deals WHERE deal_token=$1", deal_token)
        if deal:
            await message.answer(
                f"Deal {deal_token}\n{deal['amount']} TON\n{deal['description']}\n\n"
                f"💰 Wallet: `{BOT_WALLET_ADDRESS}`\n\n"
                f"Memo: `{deal['payment_token']}`\n\n"
                f"{TEXTS[lang]['system_confirms']}",
                parse_mode="Markdown"
            )
        else:
            await message.answer(TEXTS[lang]["deal_not_found"])
    else:
        await cmd_start(message)

# ----------------- START normal -----------------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (tg_id,name,lang) VALUES ($1,$2,'en') "
            "ON CONFLICT (tg_id) DO UPDATE SET name=EXCLUDED.name",
            message.from_user.id, message.from_user.full_name
        )
        row = await conn.fetchrow("SELECT lang,wallet FROM users WHERE tg_id=$1", message.from_user.id)

    lang = row["lang"] if row else "en"
    wallet = row["wallet"] if row else None

    # Start-Menü GIF + Welcome
    await bot.send_animation(
        chat_id=message.chat.id,
        animation=GIFS["start_menu"],
        caption=TEXTS[lang]["welcome"],
        reply_markup=main_menu(lang),
        parse_mode="Markdown"
    )

    if not wallet:
        await bot.send_animation(
            chat_id=message.chat.id,
            animation=GIFS["wallet"],
            caption=TEXTS[lang]["wallet_none"]
        )

# ----------------- CALLBACKS -----------------
user_states = {}

@dp.callback_query()
async def cb_all(cq: types.CallbackQuery):
    data = cq.data or ""
    uid = cq.from_user.id
    lang = await get_lang(uid)

    if data == "create_deal":
        user_states[uid] = {"flow": "create", "step": "amount"}
        await bot.send_animation(
            chat_id=cq.message.chat.id,
            animation=GIFS["deal_create"],
            caption=TEXTS[lang]["ask_amount"],
            parse_mode="Markdown"
        )
        await cq.answer()
        return

    if data == "my_deals":
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT deal_token,amount,description,status FROM deals WHERE seller_id=$1 OR buyer_id=$1", uid
            )
        if not rows:
            await cq.message.answer(TEXTS[lang]["no_deals"])
        else:
            for r in rows:
                await cq.message.answer(
                    f"Deal {r['deal_token']}\n{r['amount']} TON\n{r['description']}\nStatus: {r['status']}"
                )
        await cq.answer()
        return

    if data == "my_wallet":
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT wallet FROM users WHERE tg_id=$1", uid)
        if row and row["wallet"]:
            await cq.message.answer(TEXTS[lang]["wallet_current"].format(wallet=row["wallet"]), parse_mode="Markdown")
        else:
            await cq.message.answer(TEXTS[lang]["wallet_none"])
        await cq.answer()
        return

    if data == "change_lang":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="English 🇬🇧", callback_data="setlang:en")],
            [InlineKeyboardButton(text="Українська 🇺🇦", callback_data="setlang:uk")]
        ])
        await cq.message.answer(TEXTS[lang]["choose_lang"], reply_markup=kb)
        await cq.answer()
        return

    if data.startswith("setlang:"):
        new_lang = data.split(":")[1]
        async with pool.acquire() as conn:
            await conn.execute("UPDATE users SET lang=$1 WHERE tg_id=$2", new_lang, uid)
        await cq.message.answer(TEXTS[new_lang]["menu"], reply_markup=main_menu(new_lang))
        await cq.answer()
        return

    if data.startswith("cancel_deal:"):
        deal_token = data.split(":")[1]
        async with pool.acquire() as conn:
            deal = await conn.fetchrow("SELECT seller_id,status FROM deals WHERE deal_token=$1", deal_token)
            if not deal:
                await cq.message.answer(TEXTS[lang]["deal_not_found"])
            elif deal["seller_id"] != uid:
                await cq.message.answer("⚠️ You are not the owner of this deal.")
            elif deal["status"] != "open":
                await cq.message.answer("⚠️ Deal can no longer be cancelled.")
            else:
                await conn.execute("UPDATE deals SET status='cancelled' WHERE deal_token=$1", deal_token)
                await cq.message.edit_text(f"❌ Deal {deal_token} has been cancelled.")
        await cq.answer()
        return

# ----------------- MESSAGES -----------------
@dp.message()
async def msg_handler(message: types.Message):
    uid = message.from_user.id
    txt = (message.text or "").strip()
    lang = await get_lang(uid)

    # Wallet speichern
    if txt.startswith("UQ") and len(txt) > 30:
        async with pool.acquire() as conn:
            await conn.execute("UPDATE users SET wallet=$1 WHERE tg_id=$2", txt, uid)
        await message.answer(TEXTS[lang]["wallet_set"].format(wallet=txt), parse_mode="Markdown")
        return

    # Admin commands
    if uid in ADMIN_IDS:
        if txt.startswith("/paid "):
            raw_token = txt.split()[1]
            token = raw_token.split("-")[1] if raw_token.startswith("DEAL-") and "-" in raw_token else raw_token

            async with pool.acquire() as conn:
                deal = await conn.fetchrow(
                    "SELECT seller_id,buyer_id,amount,description FROM deals WHERE deal_token=$1", token
                )
                await conn.execute("UPDATE deals SET status='paid' WHERE deal_token=$1", token)

            # Admin sieht GIF
            await bot.send_animation(
                chat_id=message.chat.id,
                animation=GIFS["payment_received"],
                caption=TEXTS[lang]["deal_paid"].format(token=token)
            )

            if deal and deal["seller_id"]:
                buyer_info = None
                if deal and deal["buyer_id"]:
                    try:
                        user = await bot.get_chat(deal["buyer_id"])
                        buyer_info = f"@{user.username}" if user.username else user.full_name
                    except Exception:
                        buyer_info = "❓ Unknown Buyer"

                msg_text = (
                    f"💥 {TEXTS[lang]['deal_paid'].format(token=token)}\n\n"
                    f"👤 Buyer: {buyer_info}\n\n"
                    f"Deliver item to → {buyer_info}\n\n"
                    f"You will receive: {deal['amount']} TON\n"
                    f"You give: {deal['description']}\n\n"
                    f"‼️ Only hand over the goods to the person specified in the transaction.\n"
                    f"If you give them to someone else, no refund will be provided.\n"
                    f"To be safe, record a video of the delivery."
                )

                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📤 I have sent the Gift", callback_data=f"seller_sent:{token}")]
                ])

                try:
                    await bot.send_animation(
                        chat_id=deal["seller_id"],
                        animation=GIFS["payment_received"],
                        caption=msg_text,
                        reply_markup=kb
                    )
                except Exception as e:
                    await message.answer(f"⚠️ Could not notify seller: {e}")
            else:
                await message.answer(f"⚠️ No seller_id found for deal {token}. DB row: {deal}")
            return

        if txt.startswith("/payout "):
            token = txt.split()[1]
            async with pool.acquire() as conn:
                deal = await conn.fetchrow("SELECT amount FROM deals WHERE deal_token=$1", token)
                if deal:
                    amt = Decimal(deal["amount"])
                    fee = (amt * FEE_PERCENT / 100).quantize(Decimal("0.0000001"))
                    payout = (amt - fee).quantize(Decimal("0.0000001"))
                    await conn.execute("UPDATE deals SET status='payout_done' WHERE deal_token=$1", token)
                    await message.answer(TEXTS[lang]["deal_payout"].format(token=token, amount=payout, fee=fee))
            return

        if txt.startswith("/cancel "):
            token = txt.split()[1]
            async with pool.acquire() as conn:
                await conn.execute("UPDATE deals SET status='cancelled' WHERE deal_token=$1", token)
            await message.answer(TEXTS[lang]["deal_cancel"].format(token=token))
            return

    # Deal creation flow
    state = user_states.get(uid)
    if state and state["flow"] == "create":
        if state["step"] == "amount":
            try:
                amt = Decimal(txt)
                if amt <= 0:
                    raise Exception()
                state["amount"] = str(amt)
                state["step"] = "desc"
                user_states[uid] = state
                await message.answer(TEXTS[lang]["ask_desc"])
                return
            except Exception:
                await message.answer(TEXTS[lang]["ask_amount"])
                return

        elif state["step"] == "desc":
            desc = txt
            deal_token = secrets.token_hex(6)
            payment_token = f"DEAL-{deal_token}-{secrets.token_hex(4)}"
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO deals (deal_token,seller_id,seller_name,amount,description,status,payment_token,created_at)
                    VALUES ($1,$2,$3,$4,$5,'open',$6,$7)
                """, deal_token, uid, message.from_user.full_name, state["amount"], desc, payment_token, int(time.time()))
            user_states.pop(uid, None)

            # Deal erstellt: GIF + Text zusammen
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel Deal", callback_data=f"cancel_deal:{deal_token}")]
            ])
            await bot.send_animation(
                chat_id=message.chat.id,
                animation=GIFS["deal_done"],
                caption=(
                    f"{TEXTS[lang]['deal_created']}\n\n"
                    f"Token: {deal_token}\n"
                    f"Payment Token: {payment_token}\n\n"
                    f"Buyer Link:\n"
                    f"https://t.me/{(await bot.get_me()).username}?start=join_{deal_token}"
                ),
                reply_markup=kb
            )
            return

    # Fallback: Menü anzeigen
    await message.answer(TEXTS[lang]["menu"], reply_markup=main_menu(lang))

# ----------------- STARTUP -----------------
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
