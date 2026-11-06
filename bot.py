import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, PreCheckoutQuery
from aiogram.filters import CommandStart
from aiocryptopay import AioCryptoPay, Networks

# --- НАСТРОЙКИ (ВСТАВЬ СВОИ ДАННЫЕ СЮДА) ---
BOT_TOKEN = "8983777230:AAHSCWolVJ3sp4N4fmVQh_nVDPt3liXi_DI"
CRYPTO_TOKEN = "669618:AAFMDWlIPBk2c1gA9rasRADGVpaD9QANUEW"
CHANNEL_ID = -1001234567890                    # Без кавычек (с минусом)

PRICE_STARS = 100        # Цена в звездах
PRICE_CRYPTO = 1.5       # Цена в долларах (USDT)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
crypto = AioCryptoPay(token=CRYPTO_TOKEN, network=Networks.MAIN_NET)

# 1. Главное меню
@dp.message(CommandStart())
async def start(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📺 Доступ в закрытый канал", callback_data="buy_channel")]
    ])
    await m.answer("Привет! Здесь ты можешь купить доступ в наш закрытый канал.\nНажми кнопку ниже 👇", reply_markup=kb)

# 2. Выбор способа оплаты
@dp.callback_query(F.data == "buy_channel")
async def choose_payment(c: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Оплатить {PRICE_STARS} ⭐", callback_data="pay_stars")],
        [InlineKeyboardButton(text=f"Оплатить {PRICE_CRYPTO} USDT 💎", callback_data="pay_crypto")]
    ])
    await c.message.edit_text("Выбери удобный способ оплаты:", reply_markup=kb)
    await c.answer()

# 3. Оплата Звездами
@dp.callback_query(F.data == "pay_stars")
async def pay_stars(c: CallbackQuery):
    await bot.send_invoice(
        chat_id=c.from_user.id,
        title="Доступ в канал",
        description="Оплата звездами",
        payload="channel_access",
        provider_token="", 
        currency="XTR",    
        prices=[{"label": "Доступ", "amount": PRICE_STARS}],
    )
    await c.answer()

# 4. Оплата Криптой
@dp.callback_query(F.data == "pay_crypto")
async def pay_crypto(c: CallbackQuery):
    await c.message.edit_text("Генерирую счет на оплату... ⏳")
    try:
        invoice = await crypto.create_invoice(asset="USDT", amount=PRICE_CRYPTO)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Перейти к оплате", url=invoice.bot_invoice_url)]
        ])
        await c.message.edit_text(
            f"Счет на {PRICE_CRYPTO} USDT создан!\nОплати по кнопке ниже. После оплаты я пришлю ссылку в канал.",
            reply_markup=kb
        )
    except Exception as e:
        await c.message.edit_text(f"Ошибка: {e}")

# 5. Проверка оплаты звездами
@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def payment_success(message: Message):
    link = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
    await message.answer(f"✅ Оплата звездами прошла!\n\nВот твоя ссылка в канал:\n{link.invite_link}")

# 6. Фоновая проверка оплаты КРИПТОЙ
async def check_crypto_payments():
    while True:
        try:
            invoices = await crypto.get_invoices(status="paid")
            for inv in invoices:
                if inv.status == "paid" and inv.payload != "done":
                    link = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
                    await bot.send_message(
                        chat_id=inv.user_id, 
                        text=f"✅ Оплата криптой получена!\n\nТвоя ссылка в канал:\n{link.invite_link}"
                    )
                    await crypto.delete_invoice(invoice_id=inv.invoice_id)
        except Exception:
            pass
        await asyncio.sleep(10)

async def main():
    asyncio.create_task(check_crypto_payments())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
