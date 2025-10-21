from aiogram import Router, F
from aiogram.types import CallbackQuery
from database.crud import get_user_by_tg, get_vpn_profile_by_user_id
from keyboards.main import back_button

router = Router()


@router.callback_query(F.data == "profile")
async def profile_handler(callback: CallbackQuery):
    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.message.edit_text("❌ Пользователь не найден.", reply_markup=back_button)
        return

    premium_text = f"Активна до: {user.premium_until.strftime('%d.%m.%Y %H:%M')}" if user.premium_until else "Нет"

    vpn_profile = await get_vpn_profile_by_user_id(user.id)
    if vpn_profile:
        vpn_lines = [
            f"UID: {vpn_profile.uuid}",
            f"Сервер: {vpn_profile.server}:{vpn_profile.port}",
        ]
        if vpn_profile.last_sync_error:
            vpn_lines.append("Синхронизация: ⚠️ ошибка")
            vpn_lines.append(f"{vpn_profile.last_sync_error}")
        elif vpn_profile.remote_id:
            vpn_lines.append("Синхронизация: ✅ выполнена")
        else:
            vpn_lines.append("Синхронизация: ⏳ ожидает подтверждения")
    else:
        vpn_lines = [
            "Профиль не создан.",
            "Используйте кнопку 'Получить профиль' в разделе настроек.",
        ]

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

🔐 VPN профиль:
{"\n".join(vpn_lines)}
"""
    await callback.message.edit_text(profile_text, reply_markup=back_button)
