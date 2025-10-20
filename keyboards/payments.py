from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

fill_up_balance = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💸 199₽", callback_data="fill_up_199"),
     InlineKeyboardButton(text="💸 300₽", callback_data="fill_up_300")],
    [InlineKeyboardButton(text="💸 500₽", callback_data="fill_up_500"),
     InlineKeyboardButton(text="💸 1000₽", callback_data="fill_up_1000")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
])

choose_payment_method = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💎 CryptoBot", callback_data="pay_cryptobot")],
    [InlineKeyboardButton(text="💳 Карта(скоро)", callback_data="pay_bycard")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
])
