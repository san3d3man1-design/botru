import os
import asyncio
import asyncpg
import secrets
import time
import ssl
from decimal import Decimal
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",")]
BOT_WALLET_ADDRESS = os.getenv("BOT_WALLET_ADDRESS", "YOUR_WALLET")
FEE_PERCENT = Decimal(os.getenv("FEE_PERCENT") or "3.0")
DATABASE_URL = os.getenv("DATABASE_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
pool = None

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
    "ru": {
        "welcome": (
            "👋 **Добро пожаловать!**\n\n"
            "💼 Надёжный сервис для безопасных сделок!\n"
            "✨ Автоматизировано, быстро и удобно!\n\n"
            "🔷 Комиссия сервиса: всего 3 %\n"
            "🔷 Поддержка 24/7\n"
            "🔷 Отзывы пользователей: @tonundrwrld\n\n"
            "💌❤️ Теперь ваши сделки под защитой! 🛡️"
        ),
        "btn_wallet": "Добавить/Изменить кошелёк",
        "btn_deal": "Создать сделку",
        "btn_ref": "Реферальная ссылка",
        "btn_lang": "Изменить язык",
        "btn_support": "Поддержка",

        "new_deal": "Новая сделка",
        "my_deals": "Мои сделки",
        "my_wallet": "Мой кошелёк",
        "settings": "Настройки",
        "menu": "Главное меню:",
        "choose_lang": "Выберите язык:",
        "lang_menu": "Язык",
        "no_deals": "У вас ещё нет сделок.",
        "ask_amount": "Введите сумму в TON для этой сделки.\n\nПример: `10.5`",
        "ask_desc": "Теперь введите краткое описание подарка / NFT / услуги, которую вы продаёте.",
        "deal_created": "Сделка успешно создана!",
        "deal_paid": "Платёж по сделке {token} подтверждён.",
        "deal_received": "Покупатель подтвердил получение по сделке {token}.",
        "deal_payout": "Выплата по сделке {token} завершена.\n\nСумма: {amount} TON\nКомиссия: {fee} TON",
        "deal_cancel": "Сделка {token} отменена.",
        "system_confirms": "Система подтвердит автоматически после получения платежа.",
        "deal_not_found": "Сделка не найдена.",
        "wallet_set": "Ваш TON кошелёк сохранён:\n`{wallet}`",
        "wallet_current": "Текущий кошелёк:\n`{wallet}`",
        "wallet_none": "Чтобы пользоваться ботом, необходимо привязать TON кошелёк.",
        "seller_sent": (
            "Покупатель подтвердил получение товара. 📦\n"
            "Сделка успешно завершена.\n"
            "Скоро вы получите деньги на сохранённый адрес кошелька. 💸"
        ),
        "btn_seller_delivered": "Я доставил товар",
    },
    "en": {
        "welcome": (
            "👋 **Welcome!**\n\n"
            "💼 Reliable service for secure transactions!\n"
            "✨ Automated, fast, and hassle-free!\n\n"
            "🔷 Service fee: only 3 %\n"
            "🔷 Support 24/7\n"
            "🔷 User reviews: @tonundrwrld\n\n"
            "💌❤️ Now your transactions are protected! 🛡️"
        ),
        "btn_wallet": "Add/Change Wallet",
        "btn_deal": "Create a Deal",
        "btn_ref": "Referral Link",
        "btn_lang": "Change Language",
        "btn_support": "Support",

        "new_deal": "New Deal",
        "my_deals": "My Deals",
        "my_wallet": "My wallet",
        "settings": "Settings",
        "menu": "Main Menu:",
        "choose_lang": "Please choose your language:",
        "lang_menu": "Language",
        "no_deals": "You don’t have any deals yet.",
        "ask_amount": "Please enter the amount in TON for this deal.\n\nExample: `10.5`",
        "ask_desc": "Now enter a short description of the gift / NFT / service you are selling.",
        "deal_created": "Deal successfully created!",
        "deal_paid": "Payment for deal {token} confirmed.",
        "deal_received": "Buyer confirmed receipt for deal {token}.",
        "deal_payout": "Payout for deal {token} completed.\n\nAmount: {amount} TON\nFee: {fee} TON",
        "deal_cancel": "Deal {token} was cancelled.",
        "system_confirms": "The system will confirm automatically once payment is received.",
        "deal_not_found": "Deal not found.",
        "wallet_set": "Your TON wallet has been saved:\n`{wallet}`",
        "wallet_current": "Current wallet:\n`{wallet}`",
        "wallet_none": "To use this bot, you need to link your TON wallet.",
        "seller_sent": (
            "The buyer has confirmed receipt of the item. 📦\n"
            "The deal has been successfully completed.\n"
            "You will soon receive your money at the saved wallet address. 💸"
        ),
        "btn_seller_delivered": "I have delivered the item",
    }
}

# ----------------- DB INIT -----------------
async def init_db():
    global pool
    ssl_context = ssl.create_default_context(cafile=None)
    pool = await asyncpg.create_pool(DATABASE_URL, ssl=ssl_context)
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
            created_at BIGINT
        )
        """)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id BIGINT PRIMARY KEY,
            name TEXT,
            lang TEXT DEFAULT 'ru',
            wallet TEXT
        )
        """)

# ----------------- HELPERS -----------------
async def get_lang(uid):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT lang FROM users WHERE tg_id=$1", uid)
    return row["lang"] if row else "ru"

def main_menu(lang="ru"):
    t = TEXTS.get(lang, TEXTS["ru"])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["btn_wallet"], callback_data="my_wallet")],
        [InlineKeyboardButton(text=t["btn_deal"], callback_data="create_deal")],
        [InlineKeyboardButton(text=t["btn_ref"], callback_data="referral_link")],
        [InlineKeyboardButton(text=t["btn_lang"], callback_data="change_lang")],
        [InlineKeyboardButton(text=t["btn_support"], url="https://forms.gle/4kN2r57SJiPrxBjf9")]
    ])
    return kb

# ----------------- START COMMANDS -----------------
@dp.message(CommandStart(deep_link=True))
async def cmd_start_with_link(message: types.Message, command: CommandStart):
    uid = message.from_user.id
    lang = await get_lang(uid)
    token = command.args

    if token and token.startswith("join_"):
        deal_token = token.replace("join_", "")
        async with pool.acquire() as conn:
            await conn.execute("UPDATE deals SET buyer_id=$1 WHERE deal_token=$2", uid, deal_token)
            deal = await conn.fetchrow("SELECT amount,description FROM deals WHERE deal_token=$1", deal_token)
        if deal:
            await message.answer(
                f"Deal {deal_token}\n{deal['amount']} TON\n{deal['description']}\n\n"
                f"💰 Wallet: `{BOT_WALLET_ADDRESS}`\n\n"
                f"Deal Number: `{deal_token}`\n\n"
                f"{TEXTS[lang]['system_confirms']}",
                parse_mode="Markdown"
            )
        else:
            await message.answer(TEXTS[lang]["deal_not_found"])
    else:
        await cmd_start(message)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (tg_id,name,lang) VALUES ($1,$2,'ru') "
            "ON CONFLICT (tg_id) DO UPDATE SET name=EXCLUDED.name",
            message.from_user.id, message.from_user.full_name
        )
        row = await conn.fetchrow("SELECT lang,wallet FROM users WHERE tg_id=$1", message.from_user.id)

    lang = row["lang"] if row else "ru"
    wallet = row["wallet"] if row else None

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

# ----------------- CALLBACK HANDLER -----------------
user_states = {}

@dp.callback_query()
async def cb_all(cq: types.CallbackQuery):
    data = cq.data or ""
    uid = cq.from_user.id
    lang = await get_lang(uid)

    # Settings menu → Language
    if data == "change_lang":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Русский", callback_data="setlang:ru")],
            [InlineKeyboardButton(text="English", callback_data="setlang:en")]
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

    # Referral link
    if data == "referral_link":
        msg = (
            "🔗 Your referral link:\n\n"
            "https://t.me/GiftElf_Robot?start=ref=UQBgh8roDAKf3tV3G_E8z0NAVYWEZ-Quut_AWGcIECGcfn4z\n\n"
            "👥 Referral count: 1\n"
            "💰 Referral earnings: 0.00 TON\n"
            "40% of bot fees"
        )
        await cq.message.answer(msg)
        await cq.answer()
        return

    # Create deal
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

    if data == "my_wallet":
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT wallet FROM users WHERE tg_id=$1", uid)
        if row and row["wallet"]:
            await cq.message.answer(TEXTS[lang]["wallet_current"].format(wallet=row["wallet"]), parse_mode="Markdown")
        else:
            await cq.message.answer(TEXTS[lang]["wallet_none"])
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

    if data.startswith("seller_sent:"):
        deal_token = data.split(":")[1]
        async with pool.acquire() as conn:
            await conn.execute("UPDATE deals SET status='completed' WHERE deal_token=$1", deal_token)
        await cq.message.answer(TEXTS[lang]["seller_sent"])
        await cq.answer()
        return

# ----------------- MESSAGE HANDLER -----------------
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
            token = txt.split()[1]
            async with pool.acquire() as conn:
                deal = await conn.fetchrow(
                    "SELECT seller_id,buyer_id,amount,description FROM deals WHERE deal_token=$1", token
                )
                await conn.execute("UPDATE deals SET status='paid' WHERE deal_token=$1", token)

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
                    f"{TEXTS[lang]['deal_paid'].format(token=token)}\n\n"
                    f"👤 Buyer: {buyer_info}\n\n"
                    f"Deliver item to → {buyer_info}\n\n"
                    f"You will receive: {deal['amount']} TON\n"
                    f"You give: {deal['description']}\n\n"
                    f"‼️ Give goods only to the specified buyer.\n"
                    f"Better to record a video of the delivery."
                )

                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=TEXTS[lang]["btn_seller_delivered"], callback_data=f"seller_sent:{token}")]
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
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO deals (deal_token,seller_id,seller_name,amount,description,status,created_at)
                    VALUES ($1,$2,$3,$4,$5,'open',$6)
                """, deal_token, uid, message.from_user.full_name, state["amount"], desc, int(time.time()))
            user_states.pop(uid, None)

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel Deal", callback_data=f"cancel_deal:{deal_token}")]
            ])
            await bot.send_animation(
                chat_id=message.chat.id,
                animation=GIFS["deal_done"],
                caption=(
                    f"{TEXTS[lang]['deal_created']}\n\n"
                    f"Token: {deal_token}\n\n"
                    f"Buyer Link:\n"
                    f"https://t.me/{(await bot.get_me()).username}?start=join_{deal_token}"
                ),
                reply_markup=kb
            )
            return

    # Fallback
    await message.answer(TEXTS[lang]["menu"], reply_markup=main_menu(lang))

# ----------------- STARTUP -----------------
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
