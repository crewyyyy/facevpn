from aiogram import Router, F
from aiogram.types import CallbackQuery
from database.crud import get_user_by_tg, get_user_by_username
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from keyboards.main import back_button

router = Router()

ADMINS = ["enjoyoneday", "whatyousayah"]

class AdminCheck(StatesGroup):
    waiting_for_username = State()

@router.callback_query(F.data == "referral")
async def referral_handler(callback: CallbackQuery):
    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.message.edit_text("❌ Пользователь не найден.", reply_markup=back_button)
        return

    bot_username = "Facevpn_bot"
    referral_link = f"https://t.me/{bot_username}?start={user.tg_id}"

    text = (
        f"🔗 *Ваша реферальная система*\n\n"
        f"👥 Приглашено пользователей: *{user.referrals_count}*\n\n"
        f"📌 Ваша реферальная ссылка:\n"
        f"`{referral_link}`"
    )
    await callback.message.edit_text(text, reply_markup=back_button, parse_mode="Markdown")

@router.callback_query(F.data == "check_ref")
async def admin_check_ref(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.username not in ADMINS:
        await callback.answer("❌ Только админ может использовать эту кнопку.", show_alert=True)
        return

    await callback.message.edit_text("Введите @username пользователя для проверки его рефералов:")
    await state.set_state(AdminCheck.waiting_for_username)

@router.message(AdminCheck.waiting_for_username)
async def admin_receive_username(message, state: FSMContext):
    username = message.text.lstrip("@")
    user = await get_user_by_username(username)

    if not user:
        await message.answer("❌ Пользователь не найден.")
    else:
        await message.answer(f"👥 Пользователь @{username} пригласил {user.referrals_count} пользователей.", reply_markup=back_button)

    await state.clear()
