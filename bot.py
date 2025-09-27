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
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",") if x.strip()]
BOT_WALLET_ADDRESS = os.getenv("BOT_WALLET_ADDRESS", "YOUR_WALLET")
FEE_PERCENT = Decimal(os.getenv("FEE_PERCENT") or "3.0")
DATABASE_URL = os.getenv("DATABASE_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
pool = None

# ----------------- MAIN IMAGE -----------------
MAIN_IMAGE = "AgACAgUAAxkBAAIG7WjX6nozeFX2axWJ2a6SUsZzlYUqAAK2wTEblxDAVvklwsZITFijAQADAgADeAADNgQ"

# ----------------- TRANSLATIONS -----------------
TEXTS = {
    "en": {
        "welcome": (
            "👋 Welcome!\n\n"
            "💼 Reliable service for secure transactions.\n"
            "✨ Automated, fast, and hassle-free.\n\n"
            "🔷 Service fee: 3%\n"
            "🔷 Support 24/7: @rdmcd\n"
            "🔷 Reviews: @tonundrwrld\n\n"
            "🛡️ Your transactions are protected!"
        ),
        "wallet_menu": "Add/Change Wallet",
        "new_deal": "Create a Deal",
        "referrals": "Referral Link",
        "lang_menu": "Change Language",
        "no_deals": "ℹ️ You don’t have any deals yet.",
        "ask_amount": "💰 Enter **amount in TON** (example: `10.5`).",
        "ask_desc": "📝 Now enter a short description of the item/service.",
        "deal_created": "✅ Deal created successfully!",
        "deal_paid": "✅ Payment for deal {token} confirmed.",
        "deal_cancel": "❌ Deal {token} was cancelled.",
        "deal_not_found": "⚠️ Deal not found.",
        "wallet_set": "✅ Your TON wallet has been saved:\n`{wallet}`",
        "wallet_current": "👛 Current wallet:\n`{wallet}`",
        "wallet_none": "ℹ️ To receive payouts, link your TON wallet.",
        "btn_seller_delivered": "📦 I have delivered the item",
        "btn_buyer_received": "✅ I received the item",
        "seller_sent": "📦 You confirmed shipment. Waiting for buyer confirmation.",
        "buyer_prompt": "📦 Seller confirmed shipping.\n\nPlease confirm when you receive the item.",
        "buyer_confirmed": "✅ You confirmed receipt. Thank you for using our service!",
        "seller_notified": "💸 Buyer confirmed receipt. You will receive your payout soon.",
        "deal_payout": "💸 Payout for deal {token} completed.\n\nAmount: {amount} TON\nFee: {fee} TON",
    },
    "ru": {
        "welcome": (
            "👋 Добро пожаловать!\n\n"
            "💼 Надежный сервис для безопасных сделок.\n"
            "✨ Автоматизировано, быстро и удобно.\n\n"
            "🔷 Комиссия сервиса: 3%\n"
            "🔷 Поддержка 24/7: @rdmcd\n"
            "🔷 Отзывы: @tonundrwrld\n\n"
            "🛡️ Ваши сделки защищены!"
        ),
        "wallet_menu": "Добавить/Изменить кошелек",
        "new_deal": "Создать сделку",
        "referrals": "Реферальная ссылка",
        "lang_menu": "Сменить язык",
        "no_deals": "ℹ️ У вас еще нет сделок.",
        "ask_amount": "💰 Введите **сумму в TON** (например: `10.5`).",
        "ask_desc": "📝 Теперь введите короткое описание товара/услуги.",
        "deal_created": "✅ Сделка успешно создана!",
        "deal_paid": "✅ Оплата по сделке {token} подтверждена.",
        "deal_cancel": "❌ Сделка {token} отменена.",
        "deal_not_found": "⚠️ Сделка не найдена.",
        "wallet_set": "✅ Ваш TON кошелек сохранен:\n`{wallet}`",
        "wallet_current": "👛 Текущий кошелек:\n`{wallet}`",
        "wallet_none": "ℹ️ Чтобы получать выплаты, добавьте TON кошелек.",
        "btn_seller_delivered": "📦 Я отправил товар",
        "btn_buyer_received": "✅ Я получил товар",
        "seller_sent": "📦 Вы подтвердили отправку. Ждем подтверждения покупателя.",
        "buyer_prompt": "📦 Продавец подтвердил отправку.\n\nПодтвердите, когда получите товар.",
        "buyer_confirmed": "✅ Вы подтвердили получение. Спасибо за использование нашего сервиса!",
        "seller_notified": "💸 Покупатель подтвердил получение. Вы скоро получите выплату.",
        "deal_payout": "💸 Выплата по сделке {token} завершена.\n\nСумма: {amount} TON\nКомиссия: {fee} TON",
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
    t = TEXTS[lang]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 " + t["wallet_menu"], callback_data="my_wallet")],
        [InlineKeyboardButton(text="📄 " + t["new_deal"], callback_data="create_deal")],
        [InlineKeyboardButton(text="🧷 " + t["referrals"], callback_data="referrals")],
        [InlineKeyboardButton(text="🌐 " + t["lang_menu"], callback_data="settings")],
        [InlineKeyboardButton(text="📞 Support", url="https://forms.gle/4kN2r57SJiPrxBjf9")]
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
            await message.answer_photo(
                photo=MAIN_IMAGE,
                caption=f"Deal {deal_token}\n{deal['amount']} TON\n{deal['description']}\n\n💰 Wallet: `{BOT_WALLET_ADDRESS}`",
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
    lang = await get_lang(message.from_user.id)
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=MAIN_IMAGE,
        caption=TEXTS[lang]["welcome"],
        reply_markup=main_menu(lang),
        parse_mode="Markdown"
    )

# ----------------- CALLBACK HANDLER -----------------
user_states = {}

@dp.callback_query()
async def cb_all(cq: types.CallbackQuery):
    data = cq.data or ""
    uid = cq.from_user.id
    lang = await get_lang(uid)

    # Sprache ändern
    if data == "settings":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="english", callback_data="setlang:en")],
            [InlineKeyboardButton(text="русский", callback_data="setlang:ru")]
        ])
        await cq.message.answer(TEXTS[lang]["lang_menu"], reply_markup=kb)
        await cq.answer()
        return

    if data.startswith("setlang:"):
        new_lang = data.split(":")[1]
        async with pool.acquire() as conn:
            await conn.execute("UPDATE users SET lang=$1 WHERE tg_id=$2", new_lang, uid)
        await cq.message.answer(TEXTS[new_lang]["welcome"], reply_markup=main_menu(new_lang))
        await cq.answer()
        return

    # Deal erstellen
    if data == "create_deal":
        user_states[uid] = {"flow": "create", "step": "amount"}
        await bot.send_photo(cq.message.chat.id, MAIN_IMAGE, caption=TEXTS[lang]["ask_amount"], parse_mode="Markdown")
        await cq.answer()
        return

    # Eigene Deals ansehen
    if data == "my_deals":
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT deal_token,amount,description,status FROM deals WHERE seller_id=$1 OR buyer_id=$1", uid)
        if not rows:
            await cq.message.answer(TEXTS[lang]["no_deals"])
        else:
            for r in rows:
                await cq.message.answer(f"Deal {r['deal_token']}\n{r['amount']} TON\n{r['description']}\nStatus: {r['status']}")
        await cq.answer()
        return

    # Wallet anzeigen
    if data == "my_wallet":
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT wallet FROM users WHERE tg_id=$1", uid)
        if row and row["wallet"]:
            await cq.message.answer(TEXTS[lang]["wallet_current"].format(wallet=row["wallet"]), parse_mode="Markdown")
        else:
            await cq.message.answer(TEXTS[lang]["wallet_none"])
        await cq.answer()
        return

    # Deal abbrechen
    if data.startswith("cancel_deal:"):
        deal_token = data.split(":")[1]
        async with pool.acquire() as conn:
            deal = await conn.fetchrow("SELECT seller_id,status FROM deals WHERE deal_token=$1", deal_token)
            if not deal:
                await cq.message.answer(TEXTS[lang]["deal_not_found"])
            elif deal["seller_id"] != uid:
                await cq.message.answer("⚠️ Not your deal.")
            elif deal["status"] != "open":
                await cq.message.answer("⚠️ Cannot cancel.")
            else:
                await conn.execute("UPDATE deals SET status='cancelled' WHERE deal_token=$1", deal_token)
                await cq.message.edit_text(f"❌ Deal {deal_token} cancelled.")
        await cq.answer()
        return

    # Verkäufer: Ware gesendet
    if data.startswith("seller_sent:"):
        deal_token = data.split(":")[1]
        async with pool.acquire() as conn:
            deal = await conn.fetchrow("SELECT buyer_id FROM deals WHERE deal_token=$1", deal_token)
            if deal and deal["buyer_id"]:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=TEXTS[lang]["btn_buyer_received"], callback_data=f"buyer_received:{deal_token}")]
                ])
                await bot.send_photo(deal["buyer_id"], MAIN_IMAGE, caption=TEXTS[lang]["buyer_prompt"], reply_markup=kb)
            await conn.execute("UPDATE deals SET status='shipped' WHERE deal_token=$1", deal_token)
        await cq.message.answer(TEXTS[lang]["seller_sent"])
        await cq.answer()
        return

    # Käufer: Erhalt bestätigt
    if data.startswith("buyer_received:"):
        deal_token = data.split(":")[1]
        async with pool.acquire() as conn:
            deal = await conn.fetchrow("SELECT seller_id, amount FROM deals WHERE deal_token=$1", deal_token)
            if deal and deal["seller_id"]:
                await bot.send_photo(deal["seller_id"], MAIN_IMAGE, caption=TEXTS[lang]["seller_notified"])
            await conn.execute("UPDATE deals SET status='completed' WHERE deal_token=$1", deal_token)
        await cq.message.answer(TEXTS[lang]["buyer_confirmed"])
        await cq.answer()
        return

    # Referral
    if data == "referrals":
        await cq.message.answer(
            "🔗 Your referral link:\n\nhttps://t.me/GiftElf_Robot?start=ref=UQBgh8roDAKf3tV3G_E8z0NAVYWEZ-Quut_AWGcIECGcfn4z\n\n"
            "👥 Referral count: 1\n💰 Referral earnings: 0.00 TON\n40% of bot fees"
        )
        await cq.answer()
        return

# ----------------- MESSAGE HANDLER -----------------
@dp.message()
async def msg_handler(message: types.Message):
    uid = message.from_user.id
    txt = (message.text or "").strip()
    lang = await get_lang(uid)

    # Wallet speichern
    if (txt.startswith("UQ") or txt.startswith("EQ")) and len(txt) > 30:
        async with pool.acquire() as conn:
            await conn.execute("UPDATE users SET wallet=$1 WHERE tg_id=$2", txt, uid)
        await message.answer(TEXTS[lang]["wallet_set"].format(wallet=txt), parse_mode="Markdown")
        return

    # Admin-Commands
    if uid in ADMIN_IDS:
        if txt.startswith("/paid "):
            token = txt.split()[1]
            async with pool.acquire() as conn:
                await conn.execute("UPDATE deals SET status='paid' WHERE deal_token=$1", token)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=TEXTS[lang]["btn_seller_delivered"], callback_data=f"seller_sent:{token}")]
            ])
            await message.answer(TEXTS[lang]["deal_paid"].format(token=token), reply_markup=kb)
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

    # Deal-Erstellung Flow
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
            buyer_link = f"https://t.me/{(await bot.get_me()).username}?start=join_{deal_token}"
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=MAIN_IMAGE,
                caption=f"{TEXTS[lang]['deal_created']}\n\nToken: {deal_token}\n\nBuyer Link:\n{buyer_link}",
                reply_markup=kb
            )
            return

    # Fallback → Hauptmenü
    await message.answer(TEXTS[lang]["welcome"], reply_markup=main_menu(lang))

# ----------------- STARTUP -----------------
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
