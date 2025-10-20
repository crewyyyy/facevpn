from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from aiogram.exceptions import TelegramBadRequest
from database.crud import create_user, get_user_by_tg
from keyboards.main import start_buttons, generate_fruit_captcha
from datetime import datetime, timedelta
from utils.captcha import generate_captcha_image

router = Router()
captcha_answers = {}

ADMINS = ["enjoyoneday", "whatyousayah"]

CAPTCHA_LIFETIME = timedelta(minutes=2)

start_text = """
👋 Добро пожаловать в FaceVPN — твой личный щит в интернете 🛡️
🔐 Безопасность данных, скрытие IP, стабильный доступ к контенту.
🌍 Подключение к серверам по всему миру!
"""

def get_start_buttons(username: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[row[:] for row in start_buttons.inline_keyboard])
    if username in ADMINS:
        keyboard.inline_keyboard.insert(
            0,
            [InlineKeyboardButton(text="Проверить рефералов 🕵️‍♂️", callback_data="check_ref")]
        )
    return keyboard

def generate_captcha():
    return generate_fruit_captcha()

@router.message(CommandStart())
async def start_handler(message: Message, command: CommandStart):
    if message.from_user.is_bot:
        return

    user = await get_user_by_tg(message.from_user.id)
    if user:
        await message.answer(start_text, reply_markup=get_start_buttons(message.from_user.username), parse_mode=ParseMode.HTML)
        return

    args = command.args
    ref_code = None
    if args:
        try:
            ref_code = int(args)
        except ValueError:
            ref_code = None

    correct, keyboard = generate_captcha()
    image_bytes, filename = generate_captcha_image(correct)
    captcha_answers[message.from_user.id] = {
        "correct": correct,
        "ref_code": ref_code,
        "expires_at": datetime.utcnow() + CAPTCHA_LIFETIME
    }

    captcha_file = BufferedInputFile(image_bytes, filename)
    await message.answer_photo(
        captcha_file,
        caption="Привет! Чтобы подтвердить, что вы человек, выберите фрукт с изображения.",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@router.callback_query(lambda c: c.data.startswith("captcha_"))
async def captcha_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    selected = callback.data.replace("captcha_", "")
    data = captcha_answers.get(user_id)

    if not data:
        await callback.answer("❌ Время капчи истекло, попробуйте снова.", show_alert=True)
        return

    if data.get("expires_at") and data["expires_at"] < datetime.utcnow():
        captcha_answers.pop(user_id, None)
        await callback.answer("⏰ Время капчи истекло, начните заново.", show_alert=True)
        return

    if selected == data["correct"]:
        user, referrer_tg_id = await create_user(
            tg_id=user_id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
            ref_code=data["ref_code"]
        )

        if referrer_tg_id:
            try:
                await callback.bot.send_message(
                    referrer_tg_id,
                    "🎉 Ваш приглашенный пользователь прошел регистрацию! Вам начислено +7 дней премиума."
                )
            except Exception:
                pass

        captcha_answers.pop(user_id)
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass

        await callback.message.answer(
            "✅ Проверка пройдена!\n" + start_text,
            reply_markup=get_start_buttons(callback.from_user.username),
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.answer("❌ Неверно! Попробуйте снова.", show_alert=True)

@router.callback_query(F.data == "back_button")
async def back_button(callback: CallbackQuery):
    await callback.message.edit_text(
        start_text,
        reply_markup=get_start_buttons(callback.from_user.username),
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "subscribe")
async def subscribe_redirect(callback: CallbackQuery):
    from handlers.subscription import subscribe_menu
    await subscribe_menu(callback)
