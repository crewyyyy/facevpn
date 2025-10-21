from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from handlers import start, profile, subscription, vpn_settings, admin, support, referral
import logging
import os
import asyncio
from dotenv import load_dotenv
from database.session import async_main

load_dotenv()
logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=os.getenv("BOT_TOKEN"),
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher(storage=MemoryStorage())

async def main():
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(subscription.router)
    dp.include_router(vpn_settings.router)
    dp.include_router(support.router)
    dp.include_router(referral.router)
    dp.include_router(admin.router)

    await async_main()
    logging.info("Бот успешно загружен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())