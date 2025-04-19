# main.py
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import API_TOKEN, GSHEET_KEY, OPENAI_API_KEY, MANAGERS
from services.sheets_service import SheetsService
from services.gpt_service import GPTService
from handlers.form_handler import FormHandler
from handlers.history_handler import HistoryHandler
from handlers.admin_handler import AdminHandler
from handlers.gpt_handler import GPTHandler

bot = Bot(API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

sheets = SheetsService(GSHEET_KEY, 'google-credentials.json')
gpt = GPTService(OPENAI_API_KEY)

FormHandler(bot, dp, sheets, gpt).register()
HistoryHandler(bot, dp, sheets, gpt).register()
AdminHandler(bot, dp, sheets, gpt).register()
GPTHandler(bot, dp, sheets, gpt).register()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
