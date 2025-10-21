import html
import json
from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton

from database.crud import get_user_by_tg
from keyboards.main import back_button
from utils.vless import ensure_vless_profile

router = Router()

VPN_SETTINGS_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Получить профиль", callback_data="create_vless_profile")],
        [InlineKeyboardButton(text="Для телефона 📱", callback_data="Phone")],
        [InlineKeyboardButton(text="Для ПК 💻", callback_data="PC")],
        [InlineKeyboardButton(text="В главное меню 🔙", callback_data="back_button")],
    ]
)

PROFILE_RESULT_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить профиль", callback_data="create_vless_profile")],
        [InlineKeyboardButton(text="В главное меню 🔙", callback_data="back_button")],
    ]
)


@router.callback_query(F.data == "settings")
async def settings_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        """
⚙️ Подключить VPN

Нажмите «Получить профиль», чтобы создать персональный VLESS ключ. После получения ключа выберите инструкцию для своей платформы.
""",
        reply_markup=VPN_SETTINGS_KEYBOARD,
    )


@router.callback_query(F.data == "create_vless_profile")
async def create_vless_profile(callback: CallbackQuery):
    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return

    profile, created, synced, error = await ensure_vless_profile(user, force=True)

    status_line = "Профиль создан." if created else "Профиль обновлён."
    sync_line = "✅ Профиль синхронизирован с панелью." if synced else "⚠️ Не удалось автоматически синхронизировать профиль с панелью."

    details = [
        "🔐 Ваш персональный профиль FaceVPN готов!",
        status_line,
        "",
        f"UID: <code>{profile.uuid}</code>",
        f"Сервер: <code>{profile.server}</code>",
        f"Порт: <code>{profile.port}</code>",
        f"Безопасность: <code>{profile.security}</code>",
        f"Транспорт: <code>{profile.transport}</code>",
    ]

    if profile.sni:
        details.append(f"SNI/Host: <code>{profile.sni}</code>")
    if profile.path:
        details.append(f"Путь: <code>{profile.path}</code>")
    if profile.flow:
        details.append(f"Flow: <code>{profile.flow}</code>")

    details.extend([
        "",
        "Ссылка для импорта:",
        f"<code>{profile.build_uri()}</code>",
        "",
        sync_line,
    ])

    if error and not synced:
        details.append(f"Сообщение сервиса: <code>{html.escape(error)}</code>")

    await callback.message.edit_text(
        "\n".join(details),
        reply_markup=PROFILE_RESULT_KEYBOARD,
    )

    nekobox_payload = profile.to_nekobox_profile()
    json_payload = json.dumps(nekobox_payload, ensure_ascii=False, indent=2)
    document = BufferedInputFile(
        json_payload.encode("utf-8"),
        filename=f"{profile.uuid}_vless_profile.json",
    )
    await callback.message.answer_document(
        document,
        caption="JSON профиль для клиентов Nekobox/V2Ray.",
    )
    await callback.answer()


@router.callback_query(F.data == "Phone")
async def phone_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        """
1️⃣ Скачайте приложение VPN 📱
2️⃣ Скопируйте ключ сервера 🔑
3️⃣ Вставьте ключ и включите VPN""",
        reply_markup=back_button,
    )


@router.callback_query(F.data == "PC")
async def pc_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        """
1️⃣ Скачайте приложение VPN 💻
2️⃣ Выберите сервер и скопируйте ключ 🔑
3️⃣ Вставьте ключ и включите VPN""",
        reply_markup=back_button,
    )
