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

# -------- ENV --------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",") if x.strip()]
BOT_WALLET_ADDRESS = os.getenv("BOT_WALLET_ADDRESS", "YOUR_WALLET")
FEE_PERCENT = Decimal(os.getenv("FEE_PERCENT") or "3.0")
DATABASE_URL = os.getenv("DATABASE_URL")

# -------- Telegram --------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
pool = None

# Ein einziges Bild überall benutzen
IMAGE_ID = "AgACAgUAAxkBAAIG7WjX6nozeFX2axWJ2a6SUsZzlYUqAAK2wTEblxDAVvklwsZITFijAQADAgADeAADNgQ"

# -------- Texte / Übersetzungen --------
TEXTS = {
    "en": {
        "welcome": (
            "👋 <b>Welcome!</b>\n\n"
            "💼 Reliable service for secure transactions!\n"
            "✨ Automated, fast, and hassle-free!\n\n"
            "🔷 Service fee: only 3 %\n"
            "🔷 Support 24/7: @rdmcd\n"
            "🔷 User reviews: @tonundrwrld\n\n"
            "💌❤️ Now your transactions are protected! 🛡️"
        ),
        "menu": "📋 Main Menu:",
        "new_deal": "📄 Create a Deal",
        "my_wallet": "🪙 Add/Change Wallet",
        "referrals": "🧷 Referral Link",
        "lang_menu": "🌐 Change Language",
        "support": "📞 Support",

        "choose_lang": "🌐 Please choose your language:",
        "no_deals": "ℹ️ You don’t have any deals yet.",

        "ask_amount": "💰 Enter amount in TON for this deal.\n\nExample: <code>10.5</code>",
        "ask_desc": "📝 Great!\n\nNow enter a <b>short description</b> of the item/service.",

        "deal_created": "✅ Deal successfully created!",
        "deal_paid": "✅ Payment for deal {token} confirmed.",
        "deal_not_found": "⚠️ Deal not found.",
        "deal_cancel": "❌ Deal {token} was cancelled.",
        "deal_received": "📦 Buyer confirmed receipt for deal {token}.",
        "deal_payout": "💸 Payout for deal {token} completed.\n\nAmount: {amount} TON\nFee: {fee} TON",
        "seller_sent": "✅ You confirmed that you delivered the item. The buyer will now be asked to confirm receipt.",
        "buyer_confirm": "📦 The seller confirmed delivery for deal {token}.\n\nPlease confirm if you received the item.",
        "btn_seller_delivered": "📦 I have delivered the item",
        "btn_buyer_received": "✅ I confirm receipt",

        "wallet_set": "✅ Your TON wallet has been saved:\n<code>{wallet}</code>",
        "wallet_current": "👛 <b>Current wallet:</b>\n<code>{wallet}</code>",
        "wallet_none": "ℹ️ You can link your TON wallet anytime via the menu.",

        "system_confirms": "⏳ Auto-confirm after payment is detected/approved.",

        "referral_text": (
            "🔗 Your referral link:\n\n"
            "https://t.me/GiftElf_Robot?start=ref=UQBgh8roDAKf3tV3G_E8z0NAVYWEZ-Quut_AWGcIECGcfn4z\n\n"
            "👥 Referral count: 1\n"
            "💰 Referral earnings: 0.00 TON\n"
            "40% of bot fees"
        ),
    },
    "ru": {
        "welcome": (
            "👋 <b>Добро пожаловать!</b>\n\n"
            "💼 Надёжный сервис для безопасных сделок!\n"
            "✨ Автоматизировано, быстро и удобно!\n\n"
            "🔷 Комиссия сервиса: всего 3 %\n"
            "🔷 Поддержка 24/7: @rdmcd\n"
            "🔷 Отзывы: @tonundrwrld\n\n"
            "💌❤️ Теперь ваши сделки под защитой! 🛡️"
        ),
        "menu": "📋 Главное меню:",
        "new_deal": "📄 Создать сделку",
        "my_wallet": "🪙 Добавить/Изменить кошелёк",
        "referrals": "🧷 Реферальная ссылка",
        "lang_menu": "🌐 Изменить язык",
        "support": "📞 Поддержка",

        "choose_lang": "🌐 Пожалуйста, выберите язык:",
        "no_deals": "ℹ️ У вас пока нет сделок.",

        "ask_amount": "💰 Введите сумму в TON для этой сделки.\n\nПример: <code>10.5</code>",
        "ask_desc": "📝 Отлично!\n\nТеперь введите <b>краткое описание</b> товара/услуги.",

        "deal_created": "✅ Сделка успешно создана!",
        "deal_paid": "✅ Оплата по сделке {token} подтверждена.",
        "deal_not_found": "⚠️ Сделка не найдена.",
        "deal_cancel": "❌ Сделка {token} отменена.",
        "deal_received": "📦 Покупатель подтвердил получение по сделке {token}.",
        "deal_payout": "💸 Выплата по сделке {token} завершена.\n\nСумма: {amount} TON\nКомиссия: {fee} TON",
        "seller_sent": "✅ Вы подтвердили отправку товара. Теперь покупателю придёт запрос на подтверждение.",
        "buyer_confirm": "📦 Продавец подтвердил отправку по сделке {token}.\n\nПожалуйста, подтвердите получение.",
        "btn_seller_delivered": "📦 Я отправил товар",
        "btn_buyer_received": "✅ Я подтверждаю получение",

        "wallet_set": "✅ Ваш TON-кошелёк сохранён:\n<code>{wallet}</code>",
        "wallet_current": "👛 <b>Текущий кошелёк:</b>\n<code>{wallet}</code>",
        "wallet_none": "ℹ️ Вы можете добавить TON-кошелёк в меню в любое время.",

        "system_confirms": "⏳ Автоподтверждение после обнаружения/подтверждения платежа.",

        "referral_text": (
            "🔗 Ваша реферальная ссылка:\n\n"
            "https://t.me/GiftElf_Robot?start=ref=UQBgh8roDAKf3tV3G_E8z0NAVYWEZ-Quut_AWGcIECGcfn4z\n\n"
            "👥 Количество рефералов: 1\n"
            "💰 Заработано: 0.00 TON\n"
            "40% от комиссий бота"
        ),
    }
}

# -------- DB INIT --------
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

# -------- HELPERS --------
async def get_lang(uid: int) -> str:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT lang FROM users WHERE tg_id=$1", uid)
    return (row and row["lang"]) or "ru"

def main_menu(lang="ru"):
    t = TEXTS[lang]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["my_wallet"], callback_data="my_wallet")],
        [InlineKeyboardButton(text=t["new_deal"], callback_data="create_deal")],
        [InlineKeyboardButton(text=t["referrals"], callback_data="referrals")],
        [InlineKeyboardButton(text=t["lang_menu"], callback_data="change_lang")],
        [InlineKeyboardButton(text=t["support"], url="https://forms.gle/4kN2r57SJiPrxBjf9")]
    ])
    return kb

# -------- START / DEEP LINK --------
@dp.message(CommandStart(deep_link=True))
async def start_deeplink(message: types.Message, command: CommandStart):
    uid = message.from_user.id
    lang = await get_lang(uid)
    token = command.args

    if token and token.startswith("join_"):
        deal_token = token.replace("join_", "")
        async with pool.acquire() as conn:
            await conn.execute("UPDATE deals SET buyer_id=$1 WHERE deal_token=$2", uid, deal_token)
            deal = await conn.fetchrow(
                "SELECT amount,description FROM deals WHERE deal_token=$1", deal_token
            )
        if not deal:
            await message.answer(TEXTS[lang]["deal_not_found"]); return

        text = (
            f"Deal <b>{deal_token}</b>\n"
            f"<b>{deal['amount']}</b> TON\n"
            f"{deal['description']}\n\n"
            f"Send <b>exactly</b> to:\n<code>{BOT_WALLET_ADDRESS}</code>\n\n"
            f"{TEXTS[lang]['system_confirms']}"
        )
        await bot.send_photo(message.chat.id, IMAGE_ID, caption=text, parse_mode="HTML")
        return

    # Andernfalls normale /start
    await cmd_start(message)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (tg_id,name,lang) VALUES ($1,$2,'ru') "
            "ON CONFLICT (tg_id) DO UPDATE SET name=EXCLUDED.name",
            message.from_user.id, message.from_user.full_name
        )
        row = await conn.fetchrow("SELECT lang FROM users WHERE tg_id=$1", message.from_user.id)
    lang = row["lang"] if row else "ru"

    await bot.send_photo(
        chat_id=message.chat.id,
        photo=IMAGE_ID,
        caption=TEXTS[lang]["welcome"],
        reply_markup=main_menu(lang),
        parse_mode="HTML"
    )

# -------- CALLBACKS --------
user_states: dict[int, dict] = {}

@dp.callback_query()
async def cb_all(cq: types.CallbackQuery):
    data = cq.data or ""
    uid = cq.from_user.id
    lang = await get_lang(uid)

    if data == "change_lang":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="english", callback_data="setlang:en")],
            [InlineKeyboardButton(text="русский", callback_data="setlang:ru")]
        ])
        await cq.message.answer(TEXTS[lang]["choose_lang"], reply_markup=kb)
        await cq.answer(); return

    if data.startswith("setlang:"):
        new_lang = data.split(":")[1]
        async with pool.acquire() as conn:
            await conn.execute("UPDATE users SET lang=$1 WHERE tg_id=$2", new_lang, uid)
        await cq.message.answer(TEXTS[new_lang]["menu"], reply_markup=main_menu(new_lang))
        await cq.answer(); return

    if data == "my_wallet":
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT wallet FROM users WHERE tg_id=$1", uid)
        if row and row["wallet"]:
            await cq.message.answer(TEXTS[lang]["wallet_current"].format(wallet=row["wallet"]), parse_mode="HTML")
        else:
            await cq.message.answer(TEXTS[lang]["wallet_none"])
        await cq.answer(); return

    if data == "referrals":
        await cq.message.answer(TEXTS[lang]["referral_text"])
        await cq.answer(); return

    if data == "create_deal":
        user_states[uid] = {"flow": "create", "step": "amount"}
        await bot.send_photo(
            chat_id=cq.message.chat.id,
            photo=IMAGE_ID,
            caption=TEXTS[lang]["ask_amount"],
            parse_mode="HTML"
        )
        await cq.answer(); return

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
                await cq.message.edit_text(TEXTS[lang]["deal_cancel"].format(token=deal_token))
        await cq.answer(); return

    if data.startswith("seller_sent:"):
        deal_token = data.split(":")[1]
        # Verkäufer bestätigt Versand -> Käufer bekommt Button zum Bestätigen
        async with pool.acquire() as conn:
            await conn.execute("UPDATE deals SET status='delivered' WHERE deal_token=$1", deal_token)
            row = await conn.fetchrow("SELECT buyer_id FROM deals WHERE deal_token=$1", deal_token)
        await cq.message.answer(TEXTS[lang]["seller_sent"])
        if row and row["buyer_id"]:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=TEXTS[lang]["btn_buyer_received"], callback_data=f"buyer_received:{deal_token}")]
            ])
            await bot.send_message(
                chat_id=row["buyer_id"],
                text=TEXTS[lang]["buyer_confirm"].format(token=deal_token),
                reply_markup=kb
            )
        await cq.answer(); return

    if data.startswith("buyer_received:"):
        deal_token = data.split(":")[1]
        async with pool.acquire() as conn:
            await conn.execute("UPDATE deals SET status='completed' WHERE deal_token=$1", deal_token)
            row = await conn.fetchrow("SELECT seller_id FROM deals WHERE deal_token=$1", deal_token)
        if row and row["seller_id"]:
            await bot.send_message(
                chat_id=row["seller_id"],
                text=TEXTS[lang]["deal_received"].format(token=deal_token)
            )
        await cq.answer(); return

# -------- MESSAGES --------
@dp.message()
async def msg_handler(message: types.Message):
    uid = message.from_user.id
    txt = (message.text or "").strip()
    lang = await get_lang(uid)

    # Wallet setzen
    if (txt.startswith("UQ") or txt.startswith("EQ")) and len(txt) > 30:
        async with pool.acquire() as conn:
            await conn.execute("UPDATE users SET wallet=$1 WHERE tg_id=$2", txt, uid)
        await message.answer(TEXTS[lang]["wallet_set"].format(wallet=txt), parse_mode="HTML")
        return

    # ---- ADMIN COMMANDS ----
    if uid in ADMIN_IDS and txt.startswith("/"):
        parts = txt.split()
        cmd = parts[0]
        token = parts[1] if len(parts) > 1 else None

        if cmd == "/paid" and token:
    async with pool.acquire() as conn:
        deal = await conn.fetchrow(
            "SELECT seller_id,buyer_id,amount,description FROM deals WHERE deal_token=$1", token
        )
        if not deal:
            await message.answer(TEXTS[lang]["deal_not_found"]); return
        await conn.execute("UPDATE deals SET status='paid' WHERE deal_token=$1", token)

    # Admin Bestätigung (in Admin-Sprache)
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=IMAGE_ID,
        caption=TEXTS[lang]["deal_paid"].format(token=token),
        parse_mode="HTML"
    )

    # Sprache des Verkäufers holen
    seller_lang = await get_lang(deal["seller_id"]) if deal["seller_id"] else "ru"

    # Nachricht an Verkäufer (in seiner Sprache!)
    if deal and deal["seller_id"]:
        try:
            buyer_info = None
            if deal["buyer_id"]:
                user = await bot.get_chat(deal["buyer_id"])
                buyer_info = f"@{user.username}" if user.username else user.full_name
        except Exception:
            buyer_info = "❓ Unknown Buyer"

        big_text = (
            f"💥 <b>{TEXTS[seller_lang]['deal_paid'].format(token=token)}</b>\n\n"
            f"👤 <b>Buyer:</b> {buyer_info}\n\n"
            f"💸 <b>You will receive:</b> {deal['amount']} TON\n"
            f"🎁 <b>You give:</b> {deal['description']}\n\n"
            f"‼️ <b>Hand over the goods only to the specified buyer.</b>\n"
            f"If you give them to someone else, no refund will be provided.\n"
            f"For your safety, record a video of the delivery."
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=TEXTS[seller_lang]["btn_seller_delivered"], callback_data=f"seller_sent:{token}")]
        ])

        await bot.send_photo(
            chat_id=deal["seller_id"],
            photo=IMAGE_ID,
            caption=big_text,
            reply_markup=kb,
            parse_mode="HTML"
        )
                except Exception as e:
                    await message.answer(f"⚠️ Could not notify seller: {e}")

            return

        if cmd == "/payout" and token:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT amount,seller_id FROM deals WHERE deal_token=$1", token
                )
                if not row:
                    await message.answer(TEXTS[lang]["deal_not_found"]); return
                amt = Decimal(row["amount"])
                fee = (amt * FEE_PERCENT / Decimal(100)).quantize(Decimal("0.0000001"))
                payout = (amt - fee).quantize(Decimal("0.0000001"))
                await conn.execute("UPDATE deals SET status='payout_done' WHERE deal_token=$1", token)

            await message.answer(
                TEXTS[lang]["deal_payout"].format(token=token, amount=payout, fee=fee),
                parse_mode="HTML"
            )
            return

        if cmd == "/cancel" and token:
            async with pool.acquire() as conn:
                await conn.execute("UPDATE deals SET status='cancelled' WHERE deal_token=$1", token)
            await message.answer(TEXTS[lang]["deal_cancel"].format(token=token))
            return

    # ---- Deal Erstellung Flow ----
    state = user_states.get(uid)
    if state and state.get("flow") == "create":
        if state["step"] == "amount":
            try:
                amt = Decimal(txt)
                if amt <= 0:
                    raise Exception()
                state["amount"] = str(amt)
                state["step"] = "desc"
                user_states[uid] = state
                await message.answer(TEXTS[lang]["ask_desc"], parse_mode="HTML")
                return
            except Exception:
                await message.answer(TEXTS[lang]["ask_amount"], parse_mode="HTML")
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
                photo=IMAGE_ID,
                caption=(
                    f"{TEXTS[lang]['deal_created']}\n\n"
                    f"Token: <code>{deal_token}</code>\n\n"
                    f"Buyer Link:\n{buyer_link}"
                ),
                reply_markup=kb,
                parse_mode="HTML"
            )
            return

    # Fallback: Menü
    await message.answer(TEXTS[lang]["menu"], reply_markup=main_menu(lang))

# -------- STARTUP --------
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
