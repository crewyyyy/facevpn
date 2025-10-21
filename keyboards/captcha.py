import random
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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
        inline_keyboard=[[InlineKeyboardButton(text=fruit, callback_data=f"captcha_{fruit}")] for fruit in options]
    )
    return correct, keyboard
