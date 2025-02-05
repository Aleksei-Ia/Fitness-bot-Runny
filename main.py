import asyncio
import logging
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage

import db
from config import BOT_TOKEN
from handlers import router

logging.basicConfig(level=logging.INFO)


class LoggerMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            text = event.text or ''
            user_id = event.from_user.id if event.from_user else 'unknown'
            logging.info(f'[Message] User {user_id} sent: {text}')
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else 'unknown'
            data_cb = event.data
            logging.info(f'[Callback] User {user_id} pressed: {data_cb}')
        return await handler(event, data)


async def main():
    db.init_db()
    bot = Bot(token=BOT_TOKEN, parse_mode='HTML')
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(LoggerMiddleware())
    dp.callback_query.middleware(LoggerMiddleware())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
