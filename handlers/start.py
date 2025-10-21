from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from database.crud import create_user, get_user_by_tg
from keyboards.main import start_buttons, generate_fruit_captcha
from datetime import datetime, timedelta

router = Router()
captcha_answers = {}

ADMINS = ["enjoyoneday", "whatyousayah"]

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
    captcha_answers[message.from_user.id] = {"correct": correct, "ref_code": ref_code}

    await message.answer(
        f"Привет! Чтобы подтвердить, что вы человек, выберите фрукт: {correct}",
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

    if selected == data["correct"]:
        user = await create_user(
            tg_id=user_id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
            ref_code=data["ref_code"]
        )

        if data["ref_code"] and data["ref_code"] != user_id:
            referrer = await get_user_by_tg(data["ref_code"])
            if referrer:
                referrer.is_premium = True
                if not referrer.premium_until:
                    referrer.premium_until = datetime.utcnow() + timedelta(days=7)
                else:
                    referrer.premium_until += timedelta(days=7)
                try:
                    await callback.bot.send_message(
                        referrer.tg_id,
                        "🎉 Ваш приглашенный пользователь прошел регистрацию! Вам начислено +7 дней премиума."
                    )
                except:
                    pass

        captcha_answers.pop(user_id)
        await callback.message.edit_text(
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