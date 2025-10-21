from aiogram import Router, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from database.crud import get_user_by_username
from keyboards.main import back_button

router = Router()
ADMINS = ["enjoyoneday", "whatyousayah"]

class AdminCheck(StatesGroup):
    waiting_for_username = State()

@router.callback_query(F.text == "check_ref")
async def admin_check_ref(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.username not in ADMINS:
        await callback.answer("❌ Только админ может использовать эту кнопку.", show_alert=True)
        return
    await callback.message.edit_text("Введите @username пользователя для проверки рефералов:")
    await state.set_state(AdminCheck.waiting_for_username)

@router.message(AdminCheck.waiting_for_username)
async def admin_receive_username(message: Message, state: FSMContext):
    username = message.text.lstrip("@")
    user = await get_user_by_username(username)
    if not user:
        await message.answer("❌ Пользователь не найден.")
    else:
        await message.answer(f"👥 Пользователь @{username} пригласил {user.referrals_count} пользователей.", reply_markup=back_button)
    await state.clear()
