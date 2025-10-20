from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from database.crud import get_user_by_tg, add_balance, extend_premium
from keyboards.payments import fill_up_balance, choose_payment_method
import os
import logging
import json
from typing import Optional, Tuple
from aiohttp import ClientSession, ClientTimeout, ClientError
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")
CRYPTOBOT_API_URL = os.getenv("CRYPTOBOT_API_URL", "https://testnet-pay.crypt.bot/api")
CRYPTOBOT_NAME = "CryptoTestnetBot"  # Без @ для корректной ссылки

router = Router()

invoices = {}  # Храним invoice_id для чатов

# Курсы конвертации USDT -> RUB
RUB_RATES = {
    2.5: 199,
    3.8: 300,
    6.3: 500,
    12.5: 1000
}

# Дни премиума за сумму
PREMIUM_DAYS = {
    199: 7,
    300: 10,
    500: 20,
    1000: 45
}

# Состояния для оплаты
class PaymentStates(StatesGroup):
    waiting_payment = State()

@router.callback_query(F.data == "subscribe")
async def subscribe_menu(callback: CallbackQuery):
    logger.info(f"User {callback.from_user.id} opened subscription menu")
    await callback.message.edit_text(
        f"🔍 <b>Выберите сумму для пополнения: </b>",
        reply_markup=fill_up_balance,
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data.startswith("fill_up_"))
async def process_fill_up(callback: CallbackQuery, state: FSMContext):
    amount_rub = int(callback.data.split("_")[2])
    logger.info(f"User {callback.from_user.id} selected amount {amount_rub}₽")
    await state.set_state(PaymentStates.waiting_payment)
    await state.update_data(selected_amount=amount_rub)
    await callback.message.edit_text(
        f"🔍 <b>Вы выбрали пополнение на {amount_rub}₽. Выберите способ оплаты:</b>",
        reply_markup=choose_payment_method,
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "pay_cryptobot", StateFilter(PaymentStates.waiting_payment))
async def pay_with_cryptobot(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount_rub = data.get("selected_amount")
    if not amount_rub:
        logger.error(f"User {callback.from_user.id}: No amount selected")
        await callback.answer("❌ Ошибка: сумма не выбрана.", show_alert=True)
        return

    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        logger.error(f"User {callback.from_user.id} not found")
        await callback.answer("❌ Ошибка: пользователь не найден.", show_alert=True)
        return

    usdt_amount = next((usdt for usdt, rub in RUB_RATES.items() if rub == amount_rub), amount_rub / 80)
    logger.info(f"Creating invoice for user {callback.from_user.id}: {amount_rub}₽ ({usdt_amount:.2f} USDT)")

    pay_url, invoice_id = await create_invoice(usdt_amount)
    if pay_url and invoice_id:
        invoices[callback.message.chat.id] = invoice_id
        logger.info(f"Invoice created for user {callback.from_user.id}: {pay_url}")
        await callback.message.edit_text(
            f"💸 <b>Оплатите {amount_rub}₽ ({usdt_amount:.2f} USDT):</b>\n{pay_url}\n\n"
            f"Если ссылка не открывает чат с @{CRYPTOBOT_NAME}, откройте @CryptoTestnetBot и введите /start pay_{invoice_id}\n"
            f"Нажмите 'Проверить оплату' после завершения.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"💎 Оплатить {usdt_amount:.2f} USDT", url=pay_url)],
                [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_{invoice_id}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
            ]),
            parse_mode=ParseMode.HTML
        )
        await state.update_data(invoice_id=invoice_id, usdt_amount=usdt_amount)
    else:
        logger.error(f"Invoice creation failed for user {callback.from_user.id}: No pay_url or invoice_id")
        await callback.answer("❌ Не удалось создать счёт. Проверьте токен или попробуйте позже.", show_alert=True)

@router.callback_query(F.data.startswith("check_"), StateFilter(PaymentStates.waiting_payment))
async def check_payment(callback: CallbackQuery, state: FSMContext):
    chat_id = callback.message.chat.id
    telegram_id = callback.from_user.id
    raw_invoice_id = callback.data.split("_")[1]
    try:
        invoice_id = int(raw_invoice_id)
    except ValueError:
        logger.error(f"Invalid invoice id received: {raw_invoice_id}")
        await callback.answer("⚠️ Некорректный номер счета.", show_alert=True)
        return
    data = await state.get_data()
    amount_rub = data.get("selected_amount")

    logger.info(f"Checking payment for user {telegram_id}, invoice {invoice_id}")

    status_response = await check_invoice_status(invoice_id)
    if status_response and status_response.get("ok"):
        items = status_response["result"]["items"]
        invoice = next((i for i in items if int(i["invoice_id"]) == invoice_id), None)

        if invoice and invoice["status"] == "paid":
            usdt_amount = float(invoice["amount"])
            rub_amount = RUB_RATES.get(round(usdt_amount, 1), usdt_amount * 80)

            balance_updated = await add_balance(telegram_id, rub_amount)
            if not balance_updated:
                logger.warning(f"Failed to update balance for user {telegram_id}")
            days = PREMIUM_DAYS.get(amount_rub, 0)
            if days > 0:
                await extend_premium(telegram_id, days)
                logger.info(f"User {telegram_id} balance updated: {rub_amount}₽, premium extended: {days} days")
                await callback.message.edit_text(
                    f"✅ Оплата на {rub_amount}₽ прошла!\nБаланс: {rub_amount:.2f}₽\nПремиум продлён на {days} дней.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_button")]
                    ]),
                    parse_mode=ParseMode.HTML
                )
            else:
                logger.info(f"User {telegram_id} balance updated: {rub_amount}₽, no premium extension")
                await callback.message.edit_text(
                    f"✅ Оплата на {rub_amount}₽ прошла!\nБаланс: {rub_amount:.2f}₽",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_button")]
                    ]),
                    parse_mode=ParseMode.HTML
                )

            try:
                with open("qw.docx", "rb") as file:
                    await callback.message.answer_document(document=file)
                logger.info(f"Sent qw.docx to user {telegram_id}")
            except FileNotFoundError:
                logger.error(f"File qw.docx not found for user {telegram_id}")
                await callback.message.answer("⚠️ Файл qw.docx не найден.", parse_mode=ParseMode.HTML)

            invoices.pop(chat_id, None)
            await state.clear()
        else:
            logger.info(f"Payment not completed for user {telegram_id}, invoice {invoice_id}")
            await callback.answer("❌ Ещё не оплачено.", show_alert=True)
    else:
        logger.error(f"Failed to check invoice {invoice_id} for user {telegram_id}")
        await callback.answer("⚠️ Не удалось получить статус оплаты.", show_alert=True)

@router.callback_query(F.data == "back")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    logger.info(f"User {callback.from_user.id} returned to main menu")
    await state.clear()
    from handlers.start import start_text, get_start_buttons
    await callback.message.edit_text(
        start_text,
        reply_markup=get_start_buttons(callback.from_user.username),
        parse_mode=ParseMode.HTML
    )

_CLIENT_TIMEOUT = ClientTimeout(total=15)


async def create_invoice(amount: float) -> Tuple[Optional[str], Optional[int]]:
    if not CRYPTOBOT_TOKEN:
        logger.error("CRYPTOBOT_TOKEN is not configured")
        return None, None

    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    data = {
        "asset": "USDT",
        "amount": amount,
        "description": f"Пополнение баланса FaceVPN на {amount} USDT"
    }
    try:
        async with ClientSession(timeout=_CLIENT_TIMEOUT) as session:
            async with session.post(f"{CRYPTOBOT_API_URL}/createInvoice", headers=headers, json=data) as response:
                resp_text = await response.text()
                logger.debug(f"Create invoice response: {response.status} {resp_text}")
                if response.status == 200:
                    try:
                        resp_data = json.loads(resp_text)
                    except json.JSONDecodeError:
                        logger.error("Failed to decode invoice response JSON")
                        return None, None

                    if resp_data.get("ok"):
                        result = resp_data["result"]
                        return result.get("pay_url"), result.get("invoice_id")
                    logger.error(f"API error: {resp_data.get('error', 'No error details')}")
                else:
                    logger.error(f"HTTP error: {response.status} {resp_text}")
    except ClientError as e:
        logger.error(f"Request failed: {str(e)}")
    return None, None


async def check_invoice_status(invoice_id: int):
    if not CRYPTOBOT_TOKEN:
        logger.error("CRYPTOBOT_TOKEN is not configured")
        return None

    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    data = {"invoice_ids": [invoice_id]}
    try:
        async with ClientSession(timeout=_CLIENT_TIMEOUT) as session:
            async with session.post(f"{CRYPTOBOT_API_URL}/getInvoices", headers=headers, json=data) as response:
                resp_text = await response.text()
                logger.debug(f"Check invoice response: {response.status} {resp_text}")
                if response.status == 200:
                    try:
                        return json.loads(resp_text)
                    except json.JSONDecodeError:
                        logger.error("Failed to decode invoice status JSON")
                        return None
                logger.error(f"HTTP error: {response.status} {resp_text}")
    except ClientError as e:
        logger.error(f"Request failed: {str(e)}")
    return None
