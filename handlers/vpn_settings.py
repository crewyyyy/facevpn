from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.main import back_button
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

@router.callback_query(F.data == "settings")
async def settings_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        """
⚙️ Подключить VPN
Выберите инструкцию: Android или Apple.""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Для телефона 📱", callback_data="Phone")],
            [InlineKeyboardButton(text="Для ПК 💻", callback_data="PC")],
            [InlineKeyboardButton(text="В главное меню 🔙", callback_data="back_button")]
        ])
    )

@router.callback_query(F.data == "Phone")
async def phone_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        """
1️⃣ Скачайте приложение VPN 📱
2️⃣ Скопируйте ключ сервера 🔑
3️⃣ Вставьте ключ и включите VPN""",
        reply_markup=back_button
    )

@router.callback_query(F.data == "PC")
async def pc_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        """
1️⃣ Скачайте приложение VPN 💻
2️⃣ Выберите сервер и скопируйте ключ 🔑
3️⃣ Вставьте ключ и включите VPN""",
        reply_markup=back_button
    )
