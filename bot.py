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

# ----------------- ENV -----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",") if x.strip()]
BOT_WALLET_ADDRESS = os.getenv("BOT_WALLET_ADDRESS", "YOUR_WALLET")
FEE_PERCENT = Decimal(os.getenv("FEE_PERCENT") or "3.0")
DATABASE_URL = os.getenv("DATABASE_URL")

# ----------------- TELEGRAM -----------------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
pool: asyncpg.Pool | None = None

# ----------------- ONE IMAGE FOR ALL -----------------
MAIN_IMAGE = "AgACAgUAAxkBAAIG7WjX6nozeFX2axWJ2a6SUsZzlYUqAAK2wTEblxDAVvklwsZITFijAQADAgADeAADNgQ"

# ----------------- TEXTS -----------------
TEXTS = {
    "en": {
        "welcome": (
            "👋 Welcome!\n\n"
            "💼 Reliable service for secure transactions.\n"
            "✨ Automated, fast, and hassle-free.\n\n"
            "🔷 Service fee: 3%\n"
            "🔷 Support 24/7\n\n"
            "🛡️ Your transactions are protected!"
        ),
        "wallet_menu": "Add/Change Wallet",
        "new_deal": "Create a Deal",
        "referrals": "Referral Link",
        "lang_menu": "Change Language",
        "menu": "📋 Main Menu:",
        "choose_lang": "Please choose your language:",
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
        "admin_paid_seller_caption": (
            "💥 Payment for deal `{token}` confirmed.\n\n"
            "👤 Buyer: {buyer}\n\n"
            "You will receive: {amount} TON\n"
            "You give: {desc}\n\n"
            "‼️ Deliver only to the buyer shown in the transaction.\n"
            "If you give it to someone else, no refund will be provided.\n"
            "For safety, record a video of the delivery."
        ),
        "admin_paid_buyer_caption": (
            "🔒 Payment for deal `{token}` is secured in escrow.\n\n"
            "The seller is now instructed to deliver the item.\n"
            "You will get a confirmation button once the seller marks it shipped."
        ),
        "payout_text": "💸 Payout for deal {token} completed.\n\nAmount: {amount} TON\nFee: {fee} TON",
    },
    "ru": {
        "welcome": (
            "👋 Добро пожаловать!\n\n"
            "💼 Надежный сервис для безопасных сделок.\n"
            "✨ Автоматизировано, быстро и удобно.\n\n"
            "🔷 Комиссия сервиса: 3%\n"
            "🔷 Поддержка 24/7\n\n"
            "🛡️ Ваши сделки защищены!"
        ),
        "wallet_menu": "Добавить/Изменить кошелек",
        "new_deal": "Создать сделку",
        "referrals": "Реферальная ссылка",
        "lang_menu": "Сменить язык",
        "menu": "📋 Главное меню:",
        "choose_lang": "Пожалуйста, выберите язык:",
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
        "admin_paid_seller_caption": (
            "💥 Оплата по сделке `{token}` подтверждена.\n\n"
            "👤 Покупатель: {buyer}\n\n"
            "Вы получите: {amount} TON\n"
            "Вы отдаете: {desc}\n\n"
            "‼️ Передавайте товар только указанному покупателю.\n"
            "Если передадите другому, возврата не будет.\n"
            "Для безопасности запишите видео передачи."
        ),
        "admin_paid_buyer_caption": (
            "🔒 Оплата по сделке `{token}` зафиксирована на эскроу.\n\n"
            "Продавец получил инструкцию на отправку товара.\n"
            "После отметки продавцом отправки вы получите кнопку для подтверждения получения."
        ),
        "payout_text": "💸 Выплата по сделке {token} завершена.\n\nСумма: {amount} TON\nКомиссия: {fee} TON",
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
async def get_lang(uid: int) -> str:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT lang FROM users WHERE tg_id=$1", uid)
    return row["lang"] if row else "ru"

def main_menu(lang="ru") -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 " + t["wallet_menu"], callback_data="my_wallet")],
        [InlineKeyboardButton(text="📄 " + t["new_deal"], callback_data="create_deal")],
        [InlineKeyboardButton(text="🧷 " + t["referrals"], callback_data="referral_link")],
        [InlineKeyboardButton(text="🌐 " + t["lang_menu"], callback_data="settings")],
        [InlineKeyboardButton(text="📞 Support", url="https://forms.gle/4kN2r57SJiPrxBjf9")]
    ])
    return kb

# ----------------- START COMMANDS -----------------
@dp.message(CommandStart(deep_link=True))
async def cmd_start_with_link(message: types.Message, command: CommandStart):
    uid = message.from_user.id
    # Ensure user exists with default ru
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
            deal = await conn.fetchrow("SELECT amount,description FROM deals WHERE deal_token=$1", deal_token)
        if deal:
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=MAIN_IMAGE,
                caption=(
                    f"Deal {deal_token}\n{deal['amount']} TON\n{deal['description']}\n\n"
                    f"💰 Wallet: `{BOT_WALLET_ADDRESS}`\n\n"
                    f"{TEXTS[lang]['menu']}"
                ),
                parse_mode="Markdown"
            )
        else:
            await message.answer(TEXTS[lang]["deal_not_found"])
    else:
        await cmd_start(message)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (tg_id,name,lang) VALUES ($1,$2,'ru') "
            "ON CONFLICT (tg_id) DO UPDATE SET name=EXCLUDED.name",
            uid, message.from_user.full_name
        )
    lang = await get_lang(uid)
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=MAIN_IMAGE,
        caption=TEXTS[lang]["welcome"],
        reply_markup=main_menu(lang),
        parse_mode="Markdown"
    )

# ----------------- CALLBACKS -----------------
user_states: dict[int, dict] = {}

@dp.callback_query()
async def cb_all(cq: types.CallbackQuery):
    data = cq.data or ""
    uid = cq.from_user.id
    lang = await get_lang(uid)

    # Language menu (small, no emojis)
    if data == "settings":
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

    # Referral (fixed text)
    if data == "referral_link":
        await cq.message.answer(
            "🔗 Your referral link:\n\n"
            "https://t.me/GiftElf_Robot?start=ref=UQBgh8roDAKf3tV3G_E8z0NAVYWEZ-Quut_AWGcIECGcfn4z\n\n"
            "👥 Referral count: 1\n"
            "💰 Referral earnings: 0.00 TON\n"
            "40% of bot fees"
        )
        await cq.answer(); return

    # Wallet view
    if data == "my_wallet":
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT wallet FROM users WHERE tg_id=$1", uid)
        if row and row["wallet"]:
            await cq.message.answer(TEXTS[lang]["wallet_current"].format(wallet=row["wallet"]), parse_mode="Markdown")
        else:
            await cq.message.answer(TEXTS[lang]["wallet_none"])
        await cq.answer(); return

    # Create deal start
    if data == "create_deal":
        user_states[uid] = {"flow": "create", "step": "amount"}
        await bot.send_photo(cq.message.chat.id, MAIN_IMAGE, caption=TEXTS[lang]["ask_amount"], parse_mode="Markdown")
        await cq.answer(); return

    # (Optional) My deals listing – not on menu but kept if you add a button later
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

    # Cancel deal
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
                await cq.message.edit_text(TEXTS[lang]["deal_cancel"].format(token=deal_token))
        await cq.answer(); return

    # Seller confirms shipment -> notify buyer with confirm button
    if data.startswith("seller_sent:"):
        deal_token = data.split(":")[1]
        async with pool.acquire() as conn:
            deal = await conn.fetchrow("SELECT buyer_id FROM deals WHERE deal_token=$1", deal_token)
            if deal and deal["buyer_id"]:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=TEXTS[lang]["btn_buyer_received"], callback_data=f"buyer_received:{deal_token}")]
                ])
                await bot.send_photo(
                    chat_id=deal["buyer_id"],
                    photo=MAIN_IMAGE,
                    caption=TEXTS[lang]["buyer_prompt"],
                    reply_markup=kb
                )
            await conn.execute("UPDATE deals SET status='shipped' WHERE deal_token=$1", deal_token)
        await cq.message.answer(TEXTS[lang]["seller_sent"])
        await cq.answer(); return

    # Buyer confirms receipt -> notify seller
    if data.startswith("buyer_received:"):
        deal_token = data.split(":")[1]
        async with pool.acquire() as conn:
            deal = await conn.fetchrow("SELECT seller_id FROM deals WHERE deal_token=$1", deal_token)
            if deal and deal["seller_id"]:
                await bot.send_photo(
                    chat_id=deal["seller_id"],
                    photo=MAIN_IMAGE,
                    caption=TEXTS[lang]["seller_notified"]
                )
            await conn.execute("UPDATE deals SET status='completed' WHERE deal_token=$1", deal_token)
        await cq.message.answer(TEXTS[lang]["buyer_confirmed"])
        await cq.answer(); return

# ----------------- MESSAGE HANDLER -----------------
@dp.message()
async def msg_handler(message: types.Message):
    uid = message.from_user.id
    txt = (message.text or "").strip()
    lang = await get_lang(uid)

    # Save wallet
    if (txt.startswith("UQ") or txt.startswith("EQ")) and len(txt) > 30:
        async with pool.acquire() as conn:
            await conn.execute("UPDATE users SET wallet=$1 WHERE tg_id=$2", txt, uid)
        await message.answer(TEXTS[lang]["wallet_set"].format(wallet=txt), parse_mode="Markdown")
        return

    # Admin commands
    if uid in ADMIN_IDS:
        # /paid <token>  -> set status, notify seller (LONG TEXT + button), optionally notify buyer
        if txt.startswith("/paid "):
            token = txt.split(maxsplit=1)[1]
            async with pool.acquire() as conn:
                deal = await conn.fetchrow(
                    "SELECT seller_id,buyer_id,amount,description FROM deals WHERE deal_token=$1", token
                )
                if not deal:
                    await message.answer(TEXTS[lang]["deal_not_found"]); return
                await conn.execute("UPDATE deals SET status='paid' WHERE deal_token=$1", token)

            # Notify SELLER (LONG message + button)
            if deal["seller_id"]:
                # Build buyer label
                buyer_label = "❓ Unknown Buyer"
                if deal["buyer_id"]:
                    try:
                        buyer_user = await bot.get_chat(deal["buyer_id"])
                        buyer_label = f"@{buyer_user.username}" if buyer_user.username else buyer_user.full_name
                    except Exception:
                        pass

                seller_caption = TEXTS[lang]["admin_paid_seller_caption"].format(
                    token=token,
                    buyer=buyer_label,
                    amount=deal["amount"],
                    desc=deal["description"]
                )
                kb_seller = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=TEXTS[lang]["btn_seller_delivered"], callback_data=f"seller_sent:{token}")]
                ])
                await bot.send_photo(
                    chat_id=deal["seller_id"],
                    photo=MAIN_IMAGE,
                    caption=seller_caption,
                    reply_markup=kb_seller,
                    parse_mode="Markdown"
                )

            # Notify BUYER (short info escrow secured) - optional but requested now
            if deal["buyer_id"]:
                buyer_caption = TEXTS[lang]["admin_paid_buyer_caption"].format(token=token)
                try:
                    await bot.send_photo(
                        chat_id=deal["buyer_id"],
                        photo=MAIN_IMAGE,
                        caption=buyer_caption,
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

            # Acknowledge to admin
            await message.answer(TEXTS[lang]["deal_paid"].format(token=token))
            return

        # /payout <token>  -> bookkeeping text only (no chain send)
        if txt.startswith("/payout "):
            token = txt.split(maxsplit=1)[1]
            async with pool.acquire() as conn:
                row = await conn.fetchrow("SELECT amount FROM deals WHERE deal_token=$1", token)
            if row:
                amt = Decimal(row["amount"])
                fee = (amt * FEE_PERCENT / 100).quantize(Decimal("0.0000001"))
                payout = (amt - fee).quantize(Decimal("0.0000001"))
                async with pool.acquire() as conn:
                    await conn.execute("UPDATE deals SET status='payout_done' WHERE deal_token=$1", token)
                await message.answer(TEXTS[lang]["payout_text"].format(token=token, amount=payout, fee=fee))
            else:
                await message.answer(TEXTS[lang]["deal_not_found"])
            return

        # /cancel <token>
        if txt.startswith("/cancel "):
            token = txt.split(maxsplit=1)[1]
            async with pool.acquire() as conn:
                await conn.execute("UPDATE deals SET status='cancelled' WHERE deal_token=$1", token)
            await message.answer(TEXTS[lang]["deal_cancel"].format(token=token))
            return

    # Deal creation flow
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
                    f"Token: {deal_token}\n\n"
                    f"Buyer Link:\n{buyer_link}"
                ),
                reply_markup=kb
            )
            return

    # Fallback to menu
    await message.answer(TEXTS[lang]["menu"], reply_markup=main_menu(lang))

# ----------------- STARTUP -----------------
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
