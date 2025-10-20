from aiogram import Router, F
from aiogram.types import CallbackQuery
from database.crud import get_user_by_tg
from keyboards.main import back_button

router = Router()

@router.callback_query(F.data == "profile")
async def profile_handler(callback: CallbackQuery):
    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.message.edit_text("❌ Пользователь не найден.", reply_markup=back_button)
        return

    premium_text = f"Активна до: {user.premium_until.strftime('%d.%m.%Y %H:%M')}" if user.premium_until else "Нет"

    profile_text = f"""
👤 Профиль пользователя

ID Telegram: {user.tg_id}
Username: @{user.username if user.username else '-'}
Имя: {user.full_name if user.full_name else '-'}
Премиум: {"✅ Да" if user.is_premium else "❌ Нет"}
Баланс: {user.balance}
{premium_text}

Дата регистрации: {user.created_at.strftime("%d.%m.%Y %H:%M")}

🔗 Приглашено пользователей: {user.referrals_count}
"""
    await callback.message.edit_text(profile_text, reply_markup=back_button)
