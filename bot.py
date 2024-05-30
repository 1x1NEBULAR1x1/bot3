from aiogram import Dispatcher, Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import requests
from fsm import FSM
from db import create_tables
from heandlers import heandlers, accept_sending
import asyncio
from cfg import TOKEN
from callbacks import callbacks
from middlewares import SchedulerMiddlewares
from db import deactivate
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get('/')
def root():
    return {'message': 'Hello World'}

async def api():
    config = uvicorn.Config(host='0.0.0.0', port=8000, app=app)
    server = uvicorn.Server(config=config)
    await server.serve()

bot = Bot(token=TOKEN, parse_mode='html')
dp = Dispatcher()


async def start():
    print('start')
async def shutdown():
    print('shutdown')
    await deactivate()

async def main():
    await create_tables()
    scheduler = AsyncIOScheduler(timezone='Europe/Moscow')
    scheduler.start()
    dp.update.middleware.register(SchedulerMiddlewares(scheduler))
    dp.message.register(accept_sending, FSM.set_time_interval)
    dp.startup.register(start)
    dp.shutdown.register(shutdown)
    dp.include_routers(heandlers, callbacks)
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
if __name__ == "__main__":
    try:
        loop = asyncio.new_event_loop()
        loop.create_task(main())
        loop.create_task(api())
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        print('Exit')