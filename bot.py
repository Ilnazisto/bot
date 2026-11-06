import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, PreCheckoutQuery
from aiogram.filters import CommandStart
from aiocryptopay import AioCryptoPay, Networks

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8983777230:AAHSCWolVJ3sp4N4fmVQh_nVDPt3liXi_DI"         
CRYPTO_TOKEN = "669618:AAFMDWlIPBk2c1gA9rasRADGVpaD9QANUEW"       
# ID твоих трех каналов (вставь свои, они начинаются с -100...)
CHANNEL_1 = -1004307615199 # Кружочки
CHANNEL_2 = -1003994945060 # ПДФ мамочки
CHANNEL_3 = -1004306149732 # Все что есть из дп

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
crypto = AioCryptoPay(token=CRYPTO_TOKEN, network=Networks.MAIN_NET)

# 1. Главное меню (Список товаров)
@dp.message(CommandStart())
async def start(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📺 Кружочки (100 ⭐ / 1.5 $)", callback_data="buy_1")],
        [InlineKeyboardButton(text="📄 ПДФ мамочки (150 ⭐ / 2.25 $)", callback_data="buy_2")],
        [InlineKeyboardButton(text="🎁 Всё из ДП (500 ⭐ / 7.5 $)", callback_data="buy_3")]
    ])
    await m.answer("Привет! Выбери, что хочешь купить:", reply_markup=kb)

# 2. Выбор способа оплаты для каждого канала
@dp.callback_query(F.data.startswith("buy_"))
async def choose_payment(c: CallbackQuery):
    item = c.data.split("_")[1]
    
    # Определяем цены в зависимости от выбранного пункта
    if item == "1":
        stars, usd = 100, 1.5
    elif item == "2":
        stars, usd = 150, 2.25
    else:
        stars, usd = 500, 7.5
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Оплатить {stars} ⭐", callback_data=f"pay_stars_{item}")],
        [InlineKeyboardButton(text=f"Оплатить {usd} USDT 💎", callback_data=f"pay_crypto_{item}")]
    ])
    await c.message.edit_text("Выбери удобный способ оплаты:", reply_markup=kb)
    await c.answer()

# 3. Оплата Звездами
@dp.callback_query(F.data.startswith("pay_stars_"))
async def pay_stars(c: CallbackQuery):
    item = c.data.split("_")[2]
    stars = 100 if item == "1" else (150 if item == "2" else 500)
    
    await bot.send_invoice(
        chat_id=c.from_user.id,
        title=f"Доступ в канал {item}",
        description="Оплата звездами",
        payload=f"access_{item}",
        provider_token="", 
        currency="XTR",    
        prices=[{"label": "Доступ", "amount": stars}],
    )
    await c.answer()

# 4. Оплата Криптой
@dp.callback_query(F.data.startswith("pay_crypto_"))
async def pay_crypto(c: CallbackQuery):
    item = c.data.split("_")[2]
    usd = 1.5 if item == "1" else (2.25 if item == "2" else 7.5)
    
    await c.message.edit_text("Генерирую счет на оплату... ⏳")
    try:
        invoice = await crypto.create_invoice(asset="USDT", amount=usd)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Перейти к оплате", url=invoice.bot_invoice_url)]
        ])
        await c.message.edit_text(
            f"Счет на {usd} USDT создан!\nОплати по кнопке ниже. После оплаты я пришлю ссылку в канал.",
            reply_markup=kb
        )
    except Exception as e:
        await c.message.edit_text(f"Ошибка: {e}")

# 5. Проверка оплаты звездами (Выдача ссылки)
@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def payment_success(message: Message):
    payload = message.successful_payment.invoice_payload
    item = payload.split("_")[1] # Достаем цифру канала (1, 2 или 3)
    
    channel_id = CHANNEL_1 if item == "1" else (CHANNEL_2 if item == "2" else CHANNEL_3)
    link = await bot.create_chat_invite_link(chat_id=channel_id, member_limit=1)
    
    await message.answer(f"✅ Оплата звездами прошла!\n\nВот твоя ссылка в канал:\n{link.invite_link}")

# 6. Фоновая проверка оплаты КРИПТОЙ
async def check_crypto_payments():
    while True:
        try:
            invoices = await crypto.get_invoices(status="paid")
            for inv in invoices:
                if inv.status == "paid" and inv.payload != "done":
                    # В счете мы сохраняем метку канала
                    item = "1" # По умолчанию
                    if inv.description and "2" in inv.description: item = "2"
                    if inv.description and "3" in inv.description: item = "3"
                    
                    channel_id = CHANNEL_1 if item == "1" else (CHANNEL_2 if item == "2" else CHANNEL_3)
                    link = await bot.create_chat_invite_link(chat_id=channel_id, member_limit=1)
                    
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
