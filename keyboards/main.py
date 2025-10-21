from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import random

start_buttons = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Настройки VPN ⚙", callback_data="settings")],
    [InlineKeyboardButton(text="Продлить подписку 💸", callback_data="subscribe")],
    [InlineKeyboardButton(text="Профиль 👤", callback_data="profile")],
    [InlineKeyboardButton(text="Рефералка 🤝", callback_data="referral")],
    [InlineKeyboardButton(text="Новости 💾", url="https://t.me/facevpnnews")],
    [InlineKeyboardButton(text="Поддержка 📞", callback_data="support")],
    [InlineKeyboardButton(text="Лицензионное соглашение 📃", callback_data="license")]
])

setting_buttons = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Для телефона 📱", callback_data="Phone")],
    [InlineKeyboardButton(text="Для ПК 💻", callback_data="PC")],
    [InlineKeyboardButton(text="В главное меню 🔙", callback_data="back_button")]
])

back_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="В главное меню 🔙", callback_data="back_button")]
])

support_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Чат с поддержкой 🆘", url="https://t.me/facevpnsupport")],
    [InlineKeyboardButton(text="В главное меню 🔙", callback_data="back_button")]
])

def generate_fruit_captcha():
    fruits = ["🍎 Яблоко", "🍌 Банан", "🍇 Виноград", "🍉 Арбуз", "🍒 Вишня", "🥝 Киви"]
    correct = random.choice(fruits)
    options = [correct]
    while len(options) < 4:
        fruit = random.choice(fruits)
        if fruit not in options:
            options.append(fruit)
    random.shuffle(options)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=fruit, callback_data=f"captcha_{fruit}")] for fruit in options
        ]
    )
    return correct, keyboard